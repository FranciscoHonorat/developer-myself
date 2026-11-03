"""Peças HTTP genuinamente comuns: autenticação, CSRF e correlation id."""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from developer_myself.shared.correlation import set_correlation_id
from developer_myself.shared.logging import log

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


def http_error(status_code: int, detail: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"detail": detail, "code": code})
