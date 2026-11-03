"""Value objects do contexto `learning` (ADR-0002).

Imutáveis, validam a si mesmos e têm igualdade por valor.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import IntEnum, StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from developer_myself.learning.domain.errors import InvalidValueError


@dataclass(frozen=True, slots=True)
class LearnerId:
    value: uuid.UUID

    @classmethod
    def new(cls) -> LearnerId:
        return cls(uuid.uuid7())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ContentId:
    value: uuid.UUID

    @classmethod
    def new(cls) -> ContentId:
        return cls(uuid.uuid7())

    @classmethod
    def from_str(cls, value: str) -> ContentId:
        return cls(uuid.UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ChallengeId:
    value: uuid.UUID

    @classmethod
    def new(cls) -> ChallengeId:
        return cls(uuid.uuid7())

    def __str__(self) -> str:
        return str(self.value)


TITLE_MAX_LENGTH = 200


@dataclass(frozen=True, slots=True)
class Title:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned:
            raise InvalidValueError("O título não pode ser vazio.")
        if len(cleaned) > TITLE_MAX_LENGTH:
            raise InvalidValueError(f"O título deve ter no máximo {TITLE_MAX_LENGTH} caracteres.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


class ContentKind(StrEnum):
    BOOK = "BOOK"
    COURSE = "COURSE"
    ARTICLE = "ARTICLE"
    VIDEO = "VIDEO"
    OTHER = "OTHER"


class ContentStatus(StrEnum):
    LOCKED = "LOCKED"
    IN_PROGRESS = "IN_PROGRESS"
    CONSOLIDATED = "CONSOLIDATED"
    FINISHED = "FINISHED"


class SessionKind(StrEnum):
    STUDY = "STUDY"
    REVIEW = "REVIEW"


class WithheldReason(StrEnum):
    TOO_SHORT = "TOO_SHORT"
    NO_NOTES = "NO_NOTES"
    NO_REVIEW = "NO_REVIEW"
    EXPIRED = "EXPIRED"


class AbandonReason(StrEnum):
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RecallRating(IntEnum):
    """Autoavaliação antes da revisão (escala do Anki/FSRS). É o rótulo real da rede neural."""

    FORGOT = 1  # Esqueci
    HARD = 2  # Lembrei com dificuldade
    GOOD = 3  # Lembrei bem
    EASY = 4  # Fácil

    @property
    def remembered(self) -> bool:
        return self is not RecallRating.FORGOT


class MasteryLevel(StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

    @property
    def rank(self) -> int:
        """Ordem do nível. Comparar por `rank`, nunca pela string."""
        return list(MasteryLevel).index(self)

    def at_least(self, other: MasteryLevel) -> bool:
        return self.rank >= other.rank


@dataclass(frozen=True, slots=True, order=True)
class Points:
    value: int = 0

    def __post_init__(self) -> None:
        if self.value < 0:
            raise InvalidValueError("Pontos não podem ser negativos.")

    def add(self, amount: int = 1) -> Points:
        return Points(self.value + amount)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True, order=True)
class Duration:
    value: timedelta

    def __post_init__(self) -> None:
        if self.value < timedelta(0):
            raise InvalidValueError("A duração não pode ser negativa.")

    @classmethod
    def between(cls, start: datetime, end: datetime) -> Duration:
        return cls(end - start)

    @classmethod
    def minutes(cls, amount: float) -> Duration:
        return cls(timedelta(minutes=amount))

    @classmethod
    def hours(cls, amount: float) -> Duration:
        return cls(timedelta(hours=amount))

    @property
    def total_seconds(self) -> int:
        return int(self.value.total_seconds())


NOTES_MIN_CHARS = 50
NOTES_FIELD_MAX_LENGTH = 10_000


@dataclass(frozen=True, slots=True)
class Notes:
    """Anotações estruturadas: estudei / entendi / preciso revisar."""

    studied: str = ""
    understood: str = ""
    to_review: str = ""

    def __post_init__(self) -> None:
        for name in ("studied", "understood", "to_review"):
            value: str = getattr(self, name)
            if len(value) > NOTES_FIELD_MAX_LENGTH:
                raise InvalidValueError(
                    f"Cada campo das anotações aceita até {NOTES_FIELD_MAX_LENGTH} caracteres."
                )
            object.__setattr__(self, name, value.strip())

    @property
    def char_count(self) -> int:
        """Total de caracteres sem contar espaços em branco."""
        return sum(
            len("".join(field.split())) for field in (self.studied, self.understood, self.to_review)
        )

    @property
    def is_substantive(self) -> bool:
        all_filled = all((self.studied, self.understood, self.to_review))
        return all_filled and self.char_count >= NOTES_MIN_CHARS


@dataclass(frozen=True, slots=True)
class Timezone:
    name: str

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise InvalidValueError(f"Fuso horário desconhecido: {self.name!r}.") from exc

    def local_date(self, moment: datetime) -> date:
        return moment.astimezone(ZoneInfo(self.name)).date()

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Evidence:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned:
            raise InvalidValueError("A evidência não pode ser vazia.")
        if len(cleaned) > NOTES_FIELD_MAX_LENGTH:
            raise InvalidValueError("Evidência longa demais.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


MIN_DAILY_MINUTES = 60
MAX_DAILY_MINUTES = 480
WEEKDAYS = 7


@dataclass(frozen=True, slots=True)
class StudyPreferences:
    """Quanto o aprendiz estuda por dia e em quais dias da semana folga (0 = segunda)."""

    minutes_per_day: int = 210
    rest_days: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if not MIN_DAILY_MINUTES <= self.minutes_per_day <= MAX_DAILY_MINUTES:
            raise InvalidValueError(
                f"Estude entre {MIN_DAILY_MINUTES} e {MAX_DAILY_MINUTES} minutos por dia."
            )
        if any(not 0 <= d < WEEKDAYS for d in self.rest_days):
            raise InvalidValueError("Dia de folga inválido (use 0 = segunda a 6 = domingo).")
        if len(self.rest_days) >= WEEKDAYS:
            raise InvalidValueError("Deixe pelo menos um dia de estudo na semana.")
