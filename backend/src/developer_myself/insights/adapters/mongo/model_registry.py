"""Coleção `ml_models`: histórico de todos os modelos treinados (comparação e rollback)."""

from datetime import UTC
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from developer_myself.insights.application.model_registry import StoredModel

Doc = dict[str, Any]


def _model(doc: Doc) -> StoredModel:
    return StoredModel(
        id=doc["_id"],
        created_at=doc["created_at"].astimezone(UTC),
        active=doc["active"],
        payload=doc["payload"],
    )


class MongoModelRegistry:
    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._col = collection

    async def publish(self, model: StoredModel) -> None:
        doc = {
            "_id": model.id,
            "created_at": model.created_at,
            "active": model.active,
            "payload": model.payload,
        }
        await self._col.insert_one({**doc, "active": False})
        if model.active:
            # Promove: desativa os outros e ativa este. Leitores nunca veem dois ativos; por
            # um instante podem ver nenhum, e aí o provider mantém o modelo que já carregou.
            await self._col.update_many({"active": True}, {"$set": {"active": False}})
            await self._col.update_one({"_id": model.id}, {"$set": {"active": True}})

    async def active(self) -> StoredModel | None:
        doc = await self._col.find_one({"active": True}, sort=[("created_at", -1)])
        return _model(doc) if doc else None

    async def recent(self, limit: int = 10) -> list[StoredModel]:
        cursor = self._col.find({}).sort("created_at", -1).limit(limit)
        return [_model(doc) async for doc in cursor]
