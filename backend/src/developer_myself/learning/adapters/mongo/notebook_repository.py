"""Adapter Mongo do caderno: 1 documento por conteúdo (`_id` = content_id).

Toda consulta filtra também por `learner_id`: um id de outro aprendiz nunca acha nada.
"""

from datetime import UTC, datetime
from typing import Any

from pymongo import DESCENDING
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.value_objects import ContentId, LearnerId

Doc = dict[str, Any]


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _from_document(doc: Doc) -> Notebook:
    return Notebook(
        learner_id=LearnerId(doc["learner_id"]),
        content_id=ContentId(doc["_id"]),
        text=doc["text"],
        version=doc["version"],
        updated_at=_utc(doc["updated_at"]),
    )


class MongoNotebookRepository:
    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._collection = collection

    async def get(self, learner_id: LearnerId, content_id: ContentId) -> Notebook | None:
        doc = await self._collection.find_one(
            {"_id": content_id.value, "learner_id": learner_id.value}
        )
        return _from_document(doc) if doc is not None else None

    async def save(self, notebook: Notebook) -> None:
        conflict = ConcurrencyError(f"Caderno {notebook.content_id} mudou.")
        if notebook.version == 0:
            try:
                await self._collection.insert_one(
                    {
                        "_id": notebook.content_id.value,
                        "learner_id": notebook.learner_id.value,
                        "text": notebook.text,
                        "version": 1,
                        "updated_at": notebook.updated_at,
                    }
                )
            except DuplicateKeyError as exc:
                raise conflict from exc
        else:
            result = await self._collection.update_one(
                {
                    "_id": notebook.content_id.value,
                    "learner_id": notebook.learner_id.value,
                    "version": notebook.version,
                },
                {
                    "$set": {"text": notebook.text, "updated_at": notebook.updated_at},
                    "$inc": {"version": 1},
                },
            )
            if result.matched_count == 0:
                raise conflict
        notebook.version += 1

    async def list_for(self, learner_id: LearnerId) -> list[Notebook]:
        cursor = self._collection.find({"learner_id": learner_id.value}).sort(
            "updated_at", DESCENDING
        )
        return [_from_document(doc) async for doc in cursor]

    async def delete(self, learner_id: LearnerId, content_id: ContentId) -> None:
        await self._collection.delete_one({"_id": content_id.value, "learner_id": learner_id.value})

    async def delete_all(self, learner_id: LearnerId) -> None:
        await self._collection.delete_many({"learner_id": learner_id.value})
