"""Repositório em memória: passa pela MESMA suíte de contrato do Mongo (ADR-0008).

Sem broker, os eventos podem ser despachados em processo para `subscribers`
(ADR-0006: "para um usuário, despachar em processo bastaria").
"""

import copy
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.events import DomainEvent
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import LearnerId
from developer_myself.shared.correlation import get_correlation_id
from developer_myself.shared.events import envelope

Subscriber = Callable[[dict[str, Any]], Awaitable[object]]


@dataclass(slots=True)
class InMemoryStudyPlanRepository:
    subscribers: list[Subscriber] = field(default_factory=list)
    _plans: dict[LearnerId, StudyPlan] = field(default_factory=dict)
    outbox: list[DomainEvent] = field(default_factory=list)

    async def get(self, learner_id: LearnerId) -> StudyPlan | None:
        stored = self._plans.get(learner_id)
        return copy.deepcopy(stored) if stored is not None else None

    async def save(self, plan: StudyPlan) -> None:
        stored = self._plans.get(plan.id)
        current_version = stored.version if stored is not None else 0
        if plan.version != current_version:
            raise ConcurrencyError(f"Trilha {plan.id} mudou (v{current_version}).")
        events = plan.pull_events()
        self.outbox.extend(events)
        plan.version += 1
        self._plans[plan.id] = copy.deepcopy(plan)
        for event in events:
            for subscriber in self.subscribers:
                await subscriber(envelope(event, get_correlation_id()))

    async def delete(self, learner_id: LearnerId) -> None:
        self._plans.pop(learner_id, None)

    async def content_counts(self, learner_ids: list[LearnerId]) -> dict[LearnerId, int]:
        return {
            lid: len(plan.contents)
            for lid in learner_ids
            if (plan := self._plans.get(lid)) is not None
        }
