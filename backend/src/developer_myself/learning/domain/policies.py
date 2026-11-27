"""Políticas como Strategy (ADR-0002): trocar regras = nova política, sem mexer no agregado."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from developer_myself.learning.domain.value_objects import (
    Duration,
    MasteryLevel,
    Notes,
    Points,
    SessionKind,
    WithheldReason,
)

# --------------------------------------------------------------------------- pontuação


@dataclass(frozen=True, slots=True)
class ScoringContext:
    kind: SessionKind
    duration: Duration
    notes: Notes
    has_reviewable_content: bool
    last_review_on: date | None
    today: date


@dataclass(frozen=True, slots=True)
class ScoringResult:
    awarded: bool
    reason: WithheldReason | None = None

    @classmethod
    def award(cls) -> ScoringResult:
        return cls(awarded=True)

    @classmethod
    def withhold(cls, reason: WithheldReason) -> ScoringResult:
        return cls(awarded=False, reason=reason)


class ScoringPolicy(Protocol):
    def evaluate(self, ctx: ScoringContext) -> ScoringResult: ...


@dataclass(frozen=True, slots=True)
class DefaultScoringPolicy:
    """25 min ≤ duração ≤ 4 h, anotações substantivas e revisão do dia feita antes."""

    min_duration: Duration = field(default_factory=lambda: Duration.minutes(25))
    max_duration: Duration = field(default_factory=lambda: Duration.hours(4))

    def evaluate(self, ctx: ScoringContext) -> ScoringResult:
        if ctx.duration > self.max_duration:
            return ScoringResult.withhold(WithheldReason.EXPIRED)
        if ctx.duration < self.min_duration:
            return ScoringResult.withhold(WithheldReason.TOO_SHORT)
        if not ctx.notes.is_substantive:
            return ScoringResult.withhold(WithheldReason.NO_NOTES)
        reviewed_today = ctx.last_review_on == ctx.today
        if ctx.kind is SessionKind.STUDY and ctx.has_reviewable_content and not reviewed_today:
            return ScoringResult.withhold(WithheldReason.NO_REVIEW)
        return ScoringResult.award()


# --------------------------------------------------------------------------- domínio


class MasteryPolicy(Protocol):
    def level_for(
        self, points: Points, solved_challenges: Iterable[MasteryLevel]
    ) -> MasteryLevel: ...

    def requirements(self) -> Mapping[MasteryLevel, tuple[int, int]]: ...


@dataclass(frozen=True, slots=True)
class DefaultMasteryPolicy:
    """Nível = maior nível cujos requisitos (e os de todos os anteriores) estão cumpridos.

    Requisito = pontos mínimos **e** N desafios resolvidos daquele nível.
    """

    thresholds: Mapping[MasteryLevel, tuple[int, int]] = field(
        default_factory=lambda: frozendict(
            {
                MasteryLevel.INTERMEDIATE: (10, 3),
                MasteryLevel.ADVANCED: (30, 3),
            }
        )
    )

    def requirements(self) -> Mapping[MasteryLevel, tuple[int, int]]:
        return self.thresholds

    def level_for(self, points: Points, solved_challenges: Iterable[MasteryLevel]) -> MasteryLevel:
        solved = list(solved_challenges)
        reached = MasteryLevel.BEGINNER
        for level in sorted(self.thresholds, key=lambda lvl: lvl.rank):
            min_points, min_challenges = self.thresholds[level]
            solved_for_level = sum(1 for target in solved if target is level)
            if points.value >= min_points and solved_for_level >= min_challenges:
                reached = level
            else:
                break
        return reached


# --------------------------------------------------------------------------- desbloqueio


class UnlockPolicy(Protocol):
    """Quantos conteúdos podem estar em andamento e como escolher o próximo da fila.

    O domínio não conhece o catálogo: a competência e a afinidade chegam por aqui.
    """

    @property
    def max_in_progress(self) -> int: ...

    @property
    def daily_competencies(self) -> frozenset[str]:
        """Competências de hábito diário: ficam em andamento numa faixa própria, sem ocupar
        vaga, e não são consolidadas em Intermediário (só saem ao serem concluídas)."""
        ...

    def competency_of(self, title: str) -> str: ...

    def affinity(self, a: str, b: str) -> float: ...


@dataclass(frozen=True, slots=True)
class SingleTrackUnlockPolicy:
    """Padrão do domínio: um conteúdo por vez, em ordem de chegada (ADR-0002 original)."""

    max_in_progress: int = 1
    daily_competencies: frozenset[str] = frozenset()

    def competency_of(self, title: str) -> str:  # noqa: ARG002 - uma trilha só
        return "trilha"

    def affinity(self, a: str, b: str) -> float:  # noqa: ARG002
        return 0.0
