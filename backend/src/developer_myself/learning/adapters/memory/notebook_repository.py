"""Cadernos em memória: passa pela mesma suíte de contrato do Mongo (ADR-0008)."""

import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime

from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.value_objects import ContentId, LearnerId

_EPOCH = datetime.min.replace(tzinfo=UTC)


@dataclass(slots=True)
class InMemoryNotebookRepository:
    _notebooks: dict[tuple[LearnerId, ContentId], Notebook] = field(default_factory=dict)

    async def get(self, learner_id: LearnerId, content_id: ContentId) -> Notebook | None:
        stored = self._notebooks.get((learner_id, content_id))
        return copy.deepcopy(stored) if stored is not None else None

    async def save(self, notebook: Notebook) -> None:
        key = (notebook.learner_id, notebook.content_id)
        stored = self._notebooks.get(key)
        current = stored.version if stored is not None else 0
        if notebook.version != current:
            raise ConcurrencyError(f"Caderno {notebook.content_id} mudou (v{current}).")
        notebook.version += 1
        self._notebooks[key] = copy.deepcopy(notebook)

    async def list_for(self, learner_id: LearnerId) -> list[Notebook]:
        mine = [copy.deepcopy(n) for (lid, _), n in self._notebooks.items() if lid == learner_id]
        return sorted(mine, key=lambda n: n.updated_at or _EPOCH, reverse=True)

    async def delete(self, learner_id: LearnerId, content_id: ContentId) -> None:
        self._notebooks.pop((learner_id, content_id), None)

    async def delete_all(self, learner_id: LearnerId) -> None:
        for key in [k for k in self._notebooks if k[0] == learner_id]:
            del self._notebooks[key]
