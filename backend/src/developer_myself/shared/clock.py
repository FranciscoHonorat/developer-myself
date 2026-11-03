"""Port `Clock`: o tempo entra no domínio como valor (ADR-0003, I6)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(slots=True)
class FakeClock:
    """Relógio controlado para testes: `clock.advance(minutes=25)`, nunca `sleep`."""

    current: datetime = field(default_factory=lambda: datetime(2026, 11, 2, 12, 0, tzinfo=UTC))

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)

    def set(self, moment: datetime) -> None:
        self.current = moment
