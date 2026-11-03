import dataclasses
from dataclasses import dataclass, field

from developer_myself.insights.application.model_registry import StoredModel


@dataclass(slots=True)
class InMemoryModelRegistry:
    _models: list[StoredModel] = field(default_factory=list)

    async def publish(self, model: StoredModel) -> None:
        if model.active:
            self._models = [dataclasses.replace(m, active=False) for m in self._models]
        self._models.append(model)

    async def active(self) -> StoredModel | None:
        return next((m for m in reversed(self._models) if m.active), None)

    async def recent(self, limit: int = 10) -> list[StoredModel]:
        return list(reversed(self._models))[:limit]
