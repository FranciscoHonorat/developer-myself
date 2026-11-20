"""Casos de uso do caderno: erros de concorrência falam do caderno, não da trilha."""

import pytest

from developer_myself.learning.adapters.memory.notebook_repository import (
    InMemoryNotebookRepository,
)
from developer_myself.learning.adapters.memory.repository import InMemoryStudyPlanRepository
from developer_myself.learning.application.notebooks import NotebookUseCases
from developer_myself.learning.domain.errors import ConcurrencyError, NotebookConflictError
from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    LearnerId,
    Timezone,
    Title,
)
from developer_myself.shared.clock import FakeClock


class LosesTheRace(InMemoryNotebookRepository):
    """Outra aba gravou entre a leitura e o `save`."""

    async def save(self, notebook: Notebook) -> None:
        raise ConcurrencyError(f"Caderno {notebook.content_id} mudou.")


async def test_lost_race_on_save_is_a_notebook_conflict() -> None:
    clock = FakeClock()
    plans = InMemoryStudyPlanRepository()
    plan = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))
    content = plan.add_content(ContentId.new(), Title("Clean Code"), ContentKind.BOOK, clock.now())
    await plans.save(plan)
    notebooks = NotebookUseCases(plans, LosesTheRace(), clock)

    with pytest.raises(NotebookConflictError, match="caderno"):
        await notebooks.save(plan.id.value, content.id.value, "texto", 0)
