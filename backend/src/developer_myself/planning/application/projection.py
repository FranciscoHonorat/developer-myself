"""Projeção da trilha: simula os próximos dias com as regras REAIS do domínio.

Cenário otimista ("tudo pontua, todo dia, desafios resolvidos no prazo"): serve para
comparar ritmos e ordens da fila, não como promessa de data.
"""

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta

from developer_myself.insights.application.recommender import SpacedRepetitionRule
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import ContentStatus
from developer_myself.planning.application.simulation import day_blocks, morning, play

MAX_DAYS = 3 * 365


@dataclass(slots=True)
class Milestones:
    started: date | None = None
    intermediate: date | None = None
    advanced: date | None = None


@dataclass(slots=True)
class Projection:
    days: int
    milestones: dict[str, Milestones] = field(default_factory=dict)
    finished_all: bool = False

    def last(self, attr: str) -> date | None:
        values = [getattr(m, attr) for m in self.milestones.values() if getattr(m, attr)]
        return max(values) if values else None


def project(plan: StudyPlan, today: date, max_days: int = MAX_DAYS) -> Projection:
    sim = copy.deepcopy(plan)
    sim.active_session = None
    rule = SpacedRepetitionRule()
    result = Projection(days=0)
    for content in sim.contents:
        m = result.milestones.setdefault(str(content.id), Milestones())
        if content.status is not ContentStatus.LOCKED:
            m.started = today

    def on_progress(content: Content, day: date) -> None:
        m = result.milestones[str(content.id)]
        if content.status is not ContentStatus.IN_PROGRESS and m.intermediate is None:
            m.intermediate = day
        if content.status is ContentStatus.FINISHED and m.advanced is None:
            m.advanced = day
        for other in sim.contents:
            mo = result.milestones[str(other.id)]
            if other.status is not ContentStatus.LOCKED and mo.started is None:
                mo.started = day

    for offset in range(max_days):
        day = today + timedelta(days=offset)
        result.days = offset + 1
        play(sim, day_blocks(sim, rule, morning(sim, day)), on_progress)
        if all(c.status is ContentStatus.FINISHED for c in sim.contents):
            result.finished_all = True
            break
    return result
