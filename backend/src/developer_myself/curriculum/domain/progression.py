"""Ficha de competências: pontuação, ferrugem, faixas e XP (gamificação).

Regras (ver ADR-0002 para pontos e níveis):

- **Progresso de um conteúdo** (0 a 1): 70% pontos (até 30) + 15% desafios de
  Intermediário (até 3) + 15% de Avançado (até 3). Avançado completo = 1.
- **Competência = média ponderada** do progresso dos conteúdos da trilha que contam
  para ela; peso = peso da competência vezes profundidade do mapa (Profundo 3,
  Funcional 2, Noção 1). Conteúdo ainda não iniciado entra com 0 (cobertura).
- **Ferrugem:** sem revisar nem resolver desafio de um conteúdo por mais de
  21 dias (3 semanas), a contribuição dele cai 1% por dia, até o piso de 50%.
  Uma revisão, sessão de estudo ou desafio resolvido zera a ferrugem na hora.
  Os **pontos nunca diminuem** (invariante I4); só a competência efetiva cai.
- **Pico** = a competência sem ferrugem: mostra o que dá para recuperar.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from developer_myself.curriculum.domain.competencies import (
    BY_KEY,
    COMPETENCIES,
    Area,
    Competency,
    Tier,
    Weights,
)
from developer_myself.curriculum.domain.schedule import Depth

GRACE_DAYS = 21
DECAY_PER_DAY = 0.01
FRESHNESS_FLOOR = 0.5
WARNING_DAYS = 7
DEPTH_WEIGHT = {Depth.PROFUNDO: 3.0, Depth.FUNCIONAL: 2.0, Depth.NOCAO: 1.0}
XP_PER_POINT = 10
XP_PER_CHALLENGE = 25
XP_LEVEL_STEP = 50
MAX_POINTS = 30
MAX_CHALLENGES = 3
SECONDS_PER_DAY = 86_400


@dataclass(frozen=True, slots=True)
class ContentSnapshot:
    title: str
    points: int
    intermediate_solved: int
    advanced_solved: int
    last_activity: datetime | None
    depth: Depth
    skills: Weights

    @property
    def has_progress(self) -> bool:
        return self.last_activity is not None or self.points > 0

    @property
    def progress(self) -> float:
        return (
            0.70 * min(self.points, MAX_POINTS) / MAX_POINTS
            + 0.15 * min(self.intermediate_solved, MAX_CHALLENGES) / MAX_CHALLENGES
            + 0.15 * min(self.advanced_solved, MAX_CHALLENGES) / MAX_CHALLENGES
        )

    def idle_days(self, now: datetime) -> float | None:
        if self.last_activity is None:
            return None
        return max(0.0, (now - self.last_activity).total_seconds() / SECONDS_PER_DAY)

    def freshness(self, now: datetime) -> float:
        idle = self.idle_days(now)
        if idle is None or idle <= GRACE_DAYS:
            return 1.0
        return max(FRESHNESS_FLOOR, 1.0 - (idle - GRACE_DAYS) * DECAY_PER_DAY)

    def rust_in_days(self, now: datetime) -> int | None:
        """Dias até começar a enferrujar (0 = já enferrujando); None = sem progresso."""
        idle = self.idle_days(now)
        if idle is None or not self.has_progress:
            return None
        return max(0, math.ceil(GRACE_DAYS - idle))


@dataclass(frozen=True, slots=True)
class ContentContribution:
    title: str
    weight: float
    progress: float
    freshness: float
    rust_in_days: int | None


@dataclass(frozen=True, slots=True)
class CompetencyScore:
    competency: Competency
    score: float  # efetiva, com ferrugem (0 a 100)
    peak: float  # sem ferrugem
    points: float  # pontos atribuídos a esta competência
    contents: tuple[ContentContribution, ...]

    @property
    def tier(self) -> Tier:
        return Tier.of(self.score)

    @property
    def title(self) -> str:
        return f"{self.tier.value} em {self.competency.name}"

    @property
    def rust_lost(self) -> float:
        return self.peak - self.score

    @property
    def rust_in_days(self) -> int | None:
        days = [c.rust_in_days for c in self.contents if c.rust_in_days is not None]
        return min(days) if days else None

    @property
    def status(self) -> str:
        days = self.rust_in_days
        if days is None:
            return "sem progresso"
        if self.rust_lost > 0 or days == 0:
            return "enferrujando"
        if days <= WARNING_DAYS:
            return "enferruja em breve"
        return "em dia"


@dataclass(frozen=True, slots=True)
class AreaEffort:
    area: Area
    points: float


@dataclass(frozen=True, slots=True)
class Sheet:
    competencies: tuple[CompetencyScore, ...]
    effort: tuple[AreaEffort, ...]
    xp: int
    level: int
    next_level_xp: int

    @property
    def total_points(self) -> float:
        return sum(a.points for a in self.effort)


def level_for(xp: int) -> int:
    """Nível do aprendiz: cada nível exige mais XP que o anterior (curva quadrática)."""
    return math.isqrt(xp // XP_LEVEL_STEP) + 1


def build_sheet(contents: Iterable[ContentSnapshot], now: datetime) -> Sheet:
    contents = list(contents)
    sums: dict[str, list[float]] = {}  # key -> [peso, peso*progresso, peso*progresso*fresh, pts]
    parts: dict[str, list[ContentContribution]] = {}
    for c in contents:
        fresh = c.freshness(now)
        for key, share in c.skills:
            w = share * DEPTH_WEIGHT[c.depth]
            acc = sums.setdefault(key, [0.0, 0.0, 0.0, 0.0])
            acc[0] += w
            acc[1] += w * c.progress
            acc[2] += w * c.progress * fresh
            acc[3] += share * c.points
            parts.setdefault(key, []).append(
                ContentContribution(c.title, w, c.progress, fresh, c.rust_in_days(now))
            )

    scores = tuple(
        CompetencyScore(
            competency=comp,
            score=round(100 * sums[comp.key][2] / sums[comp.key][0], 1),
            peak=round(100 * sums[comp.key][1] / sums[comp.key][0], 1),
            points=sums[comp.key][3],
            contents=tuple(parts[comp.key]),
        )
        for comp in COMPETENCIES
        if comp.key in sums
    )
    effort = tuple(
        AreaEffort(area, sum(s.points for s in scores if s.competency.area is area))
        for area in Area
    )
    xp = sum(
        c.points * XP_PER_POINT + (c.intermediate_solved + c.advanced_solved) * XP_PER_CHALLENGE
        for c in contents
    )
    level = level_for(xp)
    return Sheet(scores, effort, xp, level, XP_LEVEL_STEP * level * level)


def competency(key: str) -> Competency:
    return BY_KEY[key]
