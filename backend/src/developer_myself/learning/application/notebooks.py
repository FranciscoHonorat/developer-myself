"""Casos de uso do caderno da matéria (port de entrada, ADR-0003).

O caderno vive fora do `StudyPlan`: salvar não regrava a trilha nem gera eventos.
A trilha só é LIDA para conferir que a matéria existe e é do aprendiz.
"""

import uuid
from dataclasses import dataclass

from developer_myself.learning.domain.errors import (
    ConcurrencyError,
    NotebookConflictError,
    StudyPlanNotFoundError,
)
from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.repository import NotebookRepository, StudyPlanRepository
from developer_myself.learning.domain.value_objects import ContentId, LearnerId
from developer_myself.shared.clock import Clock


@dataclass(slots=True)
class NotebookUseCases:
    plans: StudyPlanRepository
    notebooks: NotebookRepository
    clock: Clock

    async def _ensure_content(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> None:
        plan = await self.plans.get(LearnerId(learner_id))
        if plan is None:
            raise StudyPlanNotFoundError("Trilha de estudo não encontrada.")
        plan.content(ContentId(content_id))  # levanta ContentNotFoundError

    async def get(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> Notebook:
        await self._ensure_content(learner_id, content_id)
        stored = await self.notebooks.get(LearnerId(learner_id), ContentId(content_id))
        return stored or Notebook.empty(LearnerId(learner_id), ContentId(content_id))

    async def save(
        self, learner_id: uuid.UUID, content_id: uuid.UUID, text: str, version: int
    ) -> Notebook:
        notebook = await self.get(learner_id, content_id)
        notebook.edit(text, version, self.clock.now())
        try:
            await self.notebooks.save(notebook)
        except ConcurrencyError as exc:  # outra aba gravou entre a leitura e o save
            raise NotebookConflictError(
                "O caderno foi alterado em outro lugar. Recarregue antes de editar."
            ) from exc
        return notebook

    async def list(self, learner_id: uuid.UUID) -> list[Notebook]:
        return await self.notebooks.list_for(LearnerId(learner_id))
