"""Port do repositório: um por agregado, nunca por coleção (ADR-0002)."""

from typing import Protocol

from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import ContentId, LearnerId


class StudyPlanRepository(Protocol):
    async def get(self, learner_id: LearnerId) -> StudyPlan | None: ...

    async def save(self, plan: StudyPlan) -> None:
        """Grava estado + eventos pendentes; levanta `ConcurrencyError` (optimistic lock)."""
        ...

    async def delete(self, learner_id: LearnerId) -> None:
        """Exclusão da conta (LGPD, ADR-0009)."""
        ...

    async def content_counts(self, learner_ids: list[LearnerId]) -> dict[LearnerId, int]:
        """Quantidade de conteúdos por aprendiz (consulta em lote para a área de admin)."""
        ...


class NotebookRepository(Protocol):
    """Cadernos das matérias: um documento por conteúdo, sempre filtrado pelo aprendiz."""

    async def get(self, learner_id: LearnerId, content_id: ContentId) -> Notebook | None: ...

    async def save(self, notebook: Notebook) -> None:
        """Optimistic lock: levanta `ConcurrencyError`; em sucesso incrementa `version`."""
        ...

    async def list_for(self, learner_id: LearnerId) -> list[Notebook]:
        """Mais recente (`updated_at`) primeiro."""
        ...

    async def delete(self, learner_id: LearnerId, content_id: ContentId) -> None: ...

    async def delete_all(self, learner_id: LearnerId) -> None:
        """Exclusão da conta (LGPD, ADR-0009)."""
        ...
