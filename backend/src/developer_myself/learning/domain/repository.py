"""Port do repositório: um por agregado, nunca por coleção (ADR-0002)."""

from typing import Protocol

from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import LearnerId


class StudyPlanRepository(Protocol):
    async def get(self, learner_id: LearnerId) -> StudyPlan | None: ...

    async def save(self, plan: StudyPlan) -> None:
        """Grava estado + eventos pendentes; levanta `ConcurrencyError` (optimistic lock)."""
        ...

    async def delete(self, learner_id: LearnerId) -> None:
        """Exclusão da conta (LGPD, ADR-0009)."""
        ...
