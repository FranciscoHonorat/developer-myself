"""Envelope de evento: contrato público e versionado (ADR-0006).

Converte eventos de domínio (dataclasses) em dicionários de tipos primitivos.
"""

import dataclasses
import uuid
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any, ClassVar, Protocol


class Event(Protocol):
    VERSION: ClassVar[int]

    @property
    def event_id(self) -> uuid.UUID: ...

    @property
    def learner_id(self) -> uuid.UUID: ...

    @property
    def occurred_at(self) -> datetime: ...

    @classmethod
    def type_name(cls) -> str: ...


def to_primitive(value: Any) -> Any:  # noqa: PLR0911 - um retorno por tipo
    match value:
        case uuid.UUID():
            return str(value)
        case datetime():
            return value.isoformat()
        case date():
            return value.isoformat()
        case Enum():
            return value.value
        case Mapping():
            return {str(k): to_primitive(v) for k, v in value.items()}
        case list() | tuple():
            return [to_primitive(v) for v in value]
        case _:
            return value


_ENVELOPE_FIELDS = {"event_id", "learner_id", "occurred_at"}


def envelope(event: Event, correlation_id: str | None = None) -> dict[str, Any]:
    payload = {
        f.name: to_primitive(getattr(event, f.name))
        for f in dataclasses.fields(event)  # type: ignore[arg-type]
        if f.name not in _ENVELOPE_FIELDS
    }
    return {
        "event_id": str(event.event_id),
        "type": event.type_name(),
        "version": event.VERSION,
        "occurred_at": event.occurred_at.isoformat(),
        "learner_id": str(event.learner_id),
        "correlation_id": correlation_id,
        "payload": payload,
    }


def routing_key(event_type: str, version: int) -> str:
    return f"learning.{event_type}.v{version}"
