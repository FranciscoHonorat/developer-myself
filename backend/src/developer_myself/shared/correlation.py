"""`correlation_id` gerado no HTTP e propagado no envelope dos eventos (ADR-0010)."""

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None = None) -> str:
    cid = value or str(uuid.uuid7())
    _correlation_id.set(cid)
    return cid
