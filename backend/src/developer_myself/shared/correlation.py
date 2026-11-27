"""`correlation_id` gerado no HTTP e propagado no envelope dos eventos (ADR-0010)."""

import re
import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_VALID_CID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None = None) -> str:
    """Aceita apenas IDs curtos e seguros; valores inválidos viram um novo UUIDv7."""
    cid = value if value is not None and _VALID_CID.fullmatch(value) else str(uuid.uuid7())
    _correlation_id.set(cid)
    return cid
