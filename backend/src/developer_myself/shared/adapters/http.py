"""Peças HTTP genuinamente comuns: autenticação, CSRF, limites e cabeçalhos de segurança."""

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from developer_myself.shared.adapters.rate_limit import SlidingWindowLimiter
from developer_myself.shared.correlation import set_correlation_id
from developer_myself.shared.logging import log
from developer_myself.shared.settings import Settings

Authenticator = Callable[[str | None], Awaitable[uuid.UUID]]
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "x-requested-with"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
HSTS_HEADER = "max-age=31536000; includeSubDomains"


class _PayloadTooLargeError(Exception):
    pass


async def current_learner_id(request: Request) -> uuid.UUID:
    """`learner_id` vem SÓ da sessão autenticada, nunca do path/body (BOLA, ADR-0009)."""
    authenticate: Authenticator = request.app.state.authenticate
    cookie_name: str = request.app.state.settings.cookie_name
    return await authenticate(request.cookies.get(cookie_name))


LearnerIdDep = Annotated[uuid.UUID, Depends(current_learner_id)]


def _parse_content_length(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


class RequestContextMiddleware:
    """Middleware ASGI puro: correlation id, CSRF, limite de payload e cabeçalhos de segurança."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        cookie_secure: bool = True,
        max_body_bytes: int = 524_288,
    ) -> None:
        self._app = app
        self._cookie_secure = cookie_secure
        self._max_body_bytes = max_body_bytes

    def _apply_headers(self, headers: MutableHeaders, cid: str) -> None:
        headers["x-correlation-id"] = cid
        headers["x-content-type-options"] = "nosniff"
        headers["referrer-policy"] = "same-origin"
        headers["x-frame-options"] = "DENY"
        headers["content-security-policy"] = CONTENT_SECURITY_POLICY
        headers["permissions-policy"] = PERMISSIONS_POLICY
        if self._cookie_secure:
            headers["strict-transport-security"] = HSTS_HEADER

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method: str = scope["method"]
        path: str = scope["path"]
        cid = set_correlation_id(headers.get("x-correlation-id"))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                self._apply_headers(MutableHeaders(scope=message), cid)
            await send(message)

        if method in UNSAFE_METHODS and path.startswith("/api/") and not headers.get(CSRF_HEADER):
            response = JSONResponse(
                {"detail": "Cabeçalho X-Requested-With obrigatório.", "code": "CSRF"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
            await response(scope, receive, send_with_headers)
            return

        if self._max_body_bytes > 0 and method in UNSAFE_METHODS:
            declared = _parse_content_length(headers.get("content-length"))
            if declared is not None and declared > self._max_body_bytes:
                response = JSONResponse(
                    {"detail": "Corpo da requisição grande demais.", "code": "PAYLOAD_TOO_LARGE"},
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                )
                await response(scope, receive, send_with_headers)
                return

        received = 0
        response_started = False
        status_code = 500

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if self._max_body_bytes > 0 and message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max_body_bytes:
                    raise _PayloadTooLargeError
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                self._apply_headers(MutableHeaders(scope=message), cid)
            await send(message)

        start = time.perf_counter()
        try:
            await self._app(scope, limited_receive, tracked_send)
        except _PayloadTooLargeError:
            if not response_started:
                response = JSONResponse(
                    {"detail": "Corpo da requisição grande demais.", "code": "PAYLOAD_TOO_LARGE"},
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                )
                await response(scope, receive, tracked_send)
        log.info(
            "http_request",
            method=method,
            path=path,
            status=status_code,
            ms=round((time.perf_counter() - start) * 1000, 1),
        )


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
    rules: list[RateLimitRule] = []
    if s.rate_limit_registers_per_hour > 0:
        rules.append(
            RateLimitRule(
                "register",
                frozenset({"POST"}),
                SlidingWindowLimiter(s.rate_limit_registers_per_hour, 3_600),
                "/api/auth/register",
            )
        )
    if s.rate_limit_sensitive_per_minute > 0:
        # Rotas sensíveis que verificam senha com Argon2 dividem um orçamento estrito.
        sensitive = SlidingWindowLimiter(s.rate_limit_sensitive_per_minute, 60)
        rules.extend(
            [
                RateLimitRule(
                    "sensitive_auth", frozenset({"PUT"}), sensitive, "/api/auth/username"
                ),
                RateLimitRule(
                    "sensitive_auth", frozenset({"POST"}), sensitive, "/api/auth/delete-account"
                ),
            ]
        )
    if s.rate_limit_exports_per_minute > 0:
        rules.append(
            RateLimitRule(
                "export",
                frozenset({"GET"}),
                SlidingWindowLimiter(s.rate_limit_exports_per_minute, 60),
                "/api/export",
            )
        )
    if s.rate_limit_writes_per_minute > 0:
        rules.append(
            RateLimitRule(
                "write",
                UNSAFE_METHODS,
                SlidingWindowLimiter(s.rate_limit_writes_per_minute, 60),
                None,
            )
        )
    if s.rate_limit_reads_per_minute > 0:
        rules.append(
            RateLimitRule(
                "read",
                frozenset({"GET", "HEAD"}),
                SlidingWindowLimiter(s.rate_limit_reads_per_minute, 60),
                None,
            )
        )
    return rules


class RateLimitMiddleware:
    """Limita /api/* por IP do cliente (com `--proxy-headers`, o IP real atrás do proxy).

    Por IP e não pelo cookie: um cookie inventado a cada requisição furaria o limite, e
    validar a sessão aqui custaria uma ida ao banco em toda chamada.
    """

    def __init__(self, app: ASGIApp, rules: list[RateLimitRule]) -> None:
        self._app = app
        self._rules = rules

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope["path"]
        method: str = scope["method"]
        if path.startswith("/api/"):
            client_info = scope.get("client")
            client = client_info[0] if client_info else "unknown"
            rule = next((r for r in self._rules if r.matches(method, path)), None)
            retry_after = rule.limiter.hit(client) if rule else 0
            if rule and retry_after:
                log.warning("rate_limited", rule=rule.name, path=path)
                response = JSONResponse(
                    {"detail": "Muitas requisições. Aguarde um pouco.", "code": "RATE_LIMIT"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"retry-after": str(retry_after)},
                )
                await response(scope, receive, send)
                return
        await self._app(scope, receive, send)


def http_error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"detail": detail, "code": code})
