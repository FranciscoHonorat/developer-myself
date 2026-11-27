"""Eventos de domínio: no passado, imutáveis e versionados (ADR-0002, ADR-0006)."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from developer_myself.learning.domain.value_objects import (
    AbandonReason,
    ContentKind,
    MasteryLevel,
    SessionKind,
    WithheldReason,
)


def _snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    VERSION: ClassVar[int] = 1

    learner_id: uuid.UUID
    occurred_at: datetime
    event_id: uuid.UUID = field(default_factory=uuid.uuid7)

    @classmethod
    def type_name(cls) -> str:
        return _snake_case(cls.__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentAdded(DomainEvent):
    content_id: uuid.UUID
    title: str
    kind: ContentKind


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentQueued(DomainEvent):
    content_id: uuid.UUID
    blocked_by: uuid.UUID
    position: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentUnlocked(DomainEvent):
    content_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StudySessionStarted(DomainEvent):
    content_id: uuid.UUID
    kind: SessionKind
    started_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class StudySessionFinished(DomainEvent):
    """Carrega os sinais úteis para o histórico e para o ML (ADR-0012)."""

    content_id: uuid.UUID
    content_title: str
    kind: SessionKind
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    notes_studied: str
    notes_understood: str
    notes_to_review: str
    notes_char_count: int
    days_since_last_contact: int | None
    level_before: MasteryLevel
    level_after: MasteryLevel
    awarded: bool
    withheld_reason: WithheldReason | None
    # Rótulo real + sinais de ANTES da sessão (o que a rede usa para prever).
    recall_rating: int | None = None
    last_contact_days: float | None = None
    points_before: int = 0
    challenges_solved_before: int = 0
    session_count_before: int = 0
    review_count_before: int = 0
    days_since_first_session: float | None = None
    avg_notes_chars_before: float = 0.0
    last_recall_rating_before: int | None = None
    # Teste de memória da revisão (dataset da IA): um item por pergunta, na ordem.
    recall_test: tuple[dict[str, object], ...] = ()
    # Pergunta para o "eu do futuro" deixada neste estudo: {id, text, answer}.
    future_question: dict[str, object] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class WarmupFinished(DomainEvent):
    """Aquecimento concluído: teste de memória fora de sessão, sem ponto."""

    content_id: uuid.UUID
    content_title: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    recall_test: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StudySessionAbandoned(DomainEvent):
    content_id: uuid.UUID
    content_title: str
    kind: SessionKind
    started_at: datetime
    reason: AbandonReason


@dataclass(frozen=True, slots=True, kw_only=True)
class PointAwarded(DomainEvent):
    content_id: uuid.UUID
    total_points: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PointWithheld(DomainEvent):
    content_id: uuid.UUID
    reason: WithheldReason


@dataclass(frozen=True, slots=True, kw_only=True)
class ChallengeAdded(DomainEvent):
    content_id: uuid.UUID
    challenge_id: uuid.UUID
    description: str
    target_level: MasteryLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class ChallengeSolved(DomainEvent):
    content_id: uuid.UUID
    challenge_id: uuid.UUID
    target_level: MasteryLevel
    evidence: str
    seconds_to_solve: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MasteryLevelReached(DomainEvent):
    content_id: uuid.UUID
    level: MasteryLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentFinished(DomainEvent):
    content_id: uuid.UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentRemoved(DomainEvent):
    content_id: uuid.UUID
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentRenamed(DomainEvent):
    content_id: uuid.UUID
    old_title: str
    new_title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class QueueReordered(DomainEvent):
    order: tuple[uuid.UUID, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StudyPreferencesChanged(DomainEvent):
    minutes_per_day: int
    rest_days: tuple[int, ...]
    max_in_progress: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanPurposeChanged(DomainEvent):
    purpose: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentPurposeChanged(DomainEvent):
    content_id: uuid.UUID
    purpose: str | None
