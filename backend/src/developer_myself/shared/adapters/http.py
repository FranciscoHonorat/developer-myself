"""Peças HTTP genuinamente comuns: autenticação, CSRF e correlation id."""

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from developer_myself.shared.adapters.rate_limit import SlidingWindowLimiter
from developer_myself.shared.correlation import set_correlation_id
from developer_myself.shared.logging import log
from developer_myself.shared.settings import Settings

Authenticator = Callable[[str | None], Awaitable[uuid.UUID]]
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "x-requested-with"


async def current_learner_id(request: Request) -> uuid.UUID:
    """`learner_id` vem SÓ da sessão autenticada, nunca do path/body (BOLA, ADR-0009)."""
    authenticate: Authenticator = request.app.state.authenticate
    cookie_name: str = request.app.state.settings.cookie_name
    return await authenticate(request.cookies.get(cookie_name))


LearnerIdDep = Annotated[uuid.UUID, Depends(current_learner_id)]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = set_correlation_id(request.headers.get("x-correlation-id"))
        if (
            request.method in UNSAFE_METHODS
            and request.url.path.startswith("/api/")
            and not request.headers.get(CSRF_HEADER)
        ):
            response: Response = Response(
                content='{"detail":"Cabeçalho X-Requested-With obrigatório.","code":"CSRF"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json",
            )
        else:
            start = time.perf_counter()
            response = await call_next(request)
            log.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=round((time.perf_counter() - start) * 1000, 1),
            )
        response.headers["x-correlation-id"] = cid
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "same-origin"
        response.headers["x-frame-options"] = "DENY"
        return response


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    """Primeira regra que casa vence. `path=None` casa qualquer rota em /api/."""

    name: str
    methods: frozenset[str]
    limiter: SlidingWindowLimiter
    path: str | None = None

    def matches(self, method: str, path: str) -> bool:
        return method in self.methods and (self.path is None or path == self.path)


def rate_limit_rules(settings: Settings) -> list[RateLimitRule]:
    s = settings
    # (nome, métodos, acertos, janela em segundos, rota exata ou None)
    specs: list[tuple[str, frozenset[str], int, float, str | None]] = [
        (
            "register",
            frozenset({"POST"}),
            s.rate_limit_registers_per_hour,
            3_600,
            "/api/auth/register",
        ),
        ("export", frozenset({"GET"}), s.rate_limit_exports_per_minute, 60, "/api/export"),
        ("write", UNSAFE_METHODS, s.rate_limit_writes_per_minute, 60, None),
        ("read", frozenset({"GET", "HEAD"}), s.rate_limit_reads_per_minute, 60, None),
    ]
    return [
        RateLimitRule(name, methods, SlidingWindowLimiter(hits, window), path)
        for name, methods, hits, window, path in specs
        if hits > 0
    ]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limita /api/* por IP do cliente (com `--proxy-headers`, o IP real atrás do proxy).

    Por IP e não pelo cookie: um cookie inventado a cada requisição furaria o limite, e
    validar a sessão aqui custaria uma ida ao banco em toda chamada.
    """

    def __init__(self, app: ASGIApp, rules: list[RateLimitRule]) -> None:
        super().__init__(app)
        self._rules = rules

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            rule = next((r for r in self._rules if r.matches(request.method, path)), None)
            retry_after = rule.limiter.hit(client) if rule else 0
            if rule and retry_after:
                log.warning("rate_limited", rule=rule.name, path=path)
                return JSONResponse(
                    {"detail": "Muitas requisições. Aguarde um pouco.", "code": "RATE_LIMIT"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"retry-after": str(retry_after)},
                )
        return await call_next(request)


def http_error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"detail": detail, "code": code})
