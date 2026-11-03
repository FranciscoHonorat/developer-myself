"""Port do registro de modelos: todos os modelos treinados ficam guardados; um é o ativo."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StoredModel:
    id: str
    created_at: datetime
    active: bool
    payload: dict[str, Any]  # {"features": [...], "weights": {...}, "metadata": {...}}

    @property
    def metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = self.payload.get("metadata", {})
        return meta


class ModelRegistry(Protocol):
    async def publish(self, model: StoredModel) -> None:
        """Guarda o modelo; se `active`, ele passa a ser o único ativo."""
        ...

    async def active(self) -> StoredModel | None: ...

    async def recent(self, limit: int = 10) -> list[StoredModel]: ...
