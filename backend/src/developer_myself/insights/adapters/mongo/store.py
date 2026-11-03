"""Projeção `study_sessions`: só recebe inserções, idempotente por `event_id` (ADR-0006)."""

import contextlib
import dataclasses
from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from developer_myself.insights.application.history import SessionRecord

Doc = dict[str, Any]


class MongoSessionHistoryStore:
    def __init__(self, sessions: AsyncCollection[Doc], processed: AsyncCollection[Doc]) -> None:
        self._sessions = sessions
        self._processed = processed

    async def record(self, record: SessionRecord) -> bool:
        """Grava a projeção com `_id = event_id` e marca o evento como processado.

        As duas escritas são idempotentes; repetir a mensagem não duplica nada.
        """
        doc = dataclasses.asdict(record)
        doc["_id"] = doc.pop("event_id")
        inserted = True
        try:
            await self._sessions.insert_one(doc)
        except DuplicateKeyError:
            inserted = False
        with contextlib.suppress(DuplicateKeyError):
            await self._processed.insert_one({"_id": record.event_id, "seen_at": datetime.now(UTC)})
        return inserted

    async def list_for(
        self, learner_id: str, limit: int, since: datetime | None = None
    ) -> list[SessionRecord]:
        query: Doc = {"learner_id": learner_id}
        if since is not None:
            query["finished_at"] = {"$gte": since}
        return await self._find(query, sort=-1, limit=limit)

    async def _find(self, query: Doc, sort: int, limit: int) -> list[SessionRecord]:
        cursor = self._sessions.find(query).sort("finished_at", sort).limit(limit)
        records = []
        async for doc in cursor:
            doc["event_id"] = doc.pop("_id")
            doc["started_at"] = doc["started_at"].astimezone(UTC)
            doc["finished_at"] = doc["finished_at"].astimezone(UTC)
            records.append(SessionRecord(**doc))
        return records

    async def labeled_reviews(self, limit: int = 100_000) -> list[SessionRecord]:
        query = {
            "type": "study_session_finished",
            "kind": "REVIEW",
            "recall_rating": {"$ne": None},
            "last_contact_days": {"$ne": None},
        }
        return await self._find(query, sort=1, limit=limit)

    async def delete_for(self, learner_id: str) -> None:
        await self._sessions.delete_many({"learner_id": learner_id})
