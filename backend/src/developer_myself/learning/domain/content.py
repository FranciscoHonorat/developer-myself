"""Entidades `Content` e `Challenge`.

Só a raiz (`StudyPlan`) muda o estado destas entidades. Os métodos com `_` no
início são internos ao agregado (I4: pontos só mudam via `finish_session`).
"""

from dataclasses import dataclass, field
from datetime import datetime

from developer_myself.learning.domain.errors import (
    ChallengeAlreadySolvedError,
    ChallengeNotFoundError,
    InvalidTransitionError,
)
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    ContentKind,
    ContentStatus,
    Evidence,
    MasteryLevel,
    Points,
    RecallRating,
    SessionKind,
    Title,
)


@dataclass(slots=True)
class Challenge:
    id: ChallengeId
    description: str
    target_level: MasteryLevel
    created_at: datetime
    solved_at: datetime | None = None
    evidence: Evidence | None = None

    @property
    def is_solved(self) -> bool:
        return self.solved_at is not None

    def _solve(self, evidence: Evidence, now: datetime) -> None:
        if self.is_solved:
            raise ChallengeAlreadySolvedError("Este desafio já foi resolvido.")
        self.evidence = evidence
        self.solved_at = now


@dataclass(slots=True)
class Content:
    id: ContentId
    title: Title
    kind: ContentKind
    status: ContentStatus
    queued_at: datetime
    points: Points = field(default_factory=Points)
    challenges: list[Challenge] = field(default_factory=list)
    last_session_at: datetime | None = None
    finished_at: datetime | None = None
    # Sinais de memória (ADR-0012): alimentam as features da rede neural.
    first_session_at: datetime | None = None
    session_count: int = 0
    review_count: int = 0
    notes_chars_total: int = 0
    last_recall_rating: RecallRating | None = None
    consolidated_at: datetime | None = None  # None = consolidado antes deste registro existir

    # ------------------------------------------------------------------ consultas
    @property
    def session_kind(self) -> SessionKind | None:
        """O tipo da sessão é derivado do estado, nunca vem do usuário."""
        if self.status is ContentStatus.IN_PROGRESS:
            return SessionKind.STUDY
        if self.is_reviewable:
            return SessionKind.REVIEW
        return None

    @property
    def avg_notes_chars(self) -> float:
        return self.notes_chars_total / self.session_count if self.session_count else 0.0

    @property
    def has_progress(self) -> bool:
        return bool(
            self.points.value or self.session_count or any(c.is_solved for c in self.challenges)
        )

    @property
    def is_reviewable(self) -> bool:
        return self.status in {ContentStatus.CONSOLIDATED, ContentStatus.FINISHED}

    @property
    def solved_challenge_levels(self) -> list[MasteryLevel]:
        return [c.target_level for c in self.challenges if c.is_solved]

    def challenge(self, challenge_id: ChallengeId) -> Challenge:
        for challenge in self.challenges:
            if challenge.id == challenge_id:
                return challenge
        raise ChallengeNotFoundError(f"Desafio {challenge_id} não encontrado.")

    # ------------------------------------------------------------------ transições
    def _unlock(self) -> None:
        if self.status is not ContentStatus.LOCKED:
            raise InvalidTransitionError("Só um conteúdo bloqueado pode ser desbloqueado.")
        self.status = ContentStatus.IN_PROGRESS

    def _consolidate(self, now: datetime | None = None) -> None:
        if self.status is not ContentStatus.IN_PROGRESS:
            raise InvalidTransitionError("Só um conteúdo em andamento pode ser consolidado.")
        self.status = ContentStatus.CONSOLIDATED
        self.consolidated_at = now

    def _finish(self, now: datetime) -> None:
        if self.status not in {ContentStatus.IN_PROGRESS, ContentStatus.CONSOLIDATED}:
            raise InvalidTransitionError(
                "Só um conteúdo em andamento ou consolidado pode ser concluído."
            )
        self.status = ContentStatus.FINISHED
        self.finished_at = now

    def _award_point(self) -> None:
        self.points = self.points.add(1)

    def _register_session(
        self, now: datetime, kind: SessionKind, notes_chars: int, rating: RecallRating | None
    ) -> None:
        self.last_session_at = now
        self.first_session_at = self.first_session_at or now
        self.session_count += 1
        self.notes_chars_total += notes_chars
        if kind is SessionKind.REVIEW:
            self.review_count += 1
            self.last_recall_rating = rating
