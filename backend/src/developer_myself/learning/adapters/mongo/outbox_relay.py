"""Relay do outbox: publica e SÓ DEPOIS remove os eventos confirmados (ADR-0006).

At-least-once: se o processo cair entre publicar e o `$pull`, o evento é publicado
de novo, e os consumers são idempotentes.
"""

import asyncio
import contextlib
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from developer_myself.shared.logging import log

Doc = dict[str, Any]
Publish = Callable[[dict[str, Any]], Awaitable[None]]


def _to_wire(entry: Doc) -> Doc:
    wire = dict(entry)
    wire["event_id"] = str(entry["event_id"])
    if isinstance(wire.get("occurred_at"), datetime):
        wire["occurred_at"] = wire["occurred_at"].isoformat()
    return wire


class OutboxRelay:
    def __init__(self, plans: AsyncCollection[Doc], publish: Publish, batch_size: int = 50) -> None:
        self._plans = plans
        self._publish = publish
        self._batch_size = batch_size

    async def run_once(self) -> int:
        published = 0
        cursor = self._plans.find({"has_outbox": True}, {"outbox": 1}).limit(self._batch_size)
        async for doc in cursor:
            done: list[uuid.UUID] = []
            for entry in doc.get("outbox", []):
                try:
                    await self._publish(_to_wire(entry))
                except Exception:
                    log.exception("outbox_publish_failed", event_id=str(entry["event_id"]))
                    break
                done.append(entry["event_id"])
            if done:
                await self._plans.update_one(
                    {"_id": doc["_id"]}, {"$pull": {"outbox": {"event_id": {"$in": done}}}}
                )
                published += len(done)
            # Só desliga a flag se ninguém tiver empurrado eventos novos nesse meio-tempo.
            await self._plans.update_one(
                {"_id": doc["_id"], "outbox": {"$size": 0}}, {"$set": {"has_outbox": False}}
            )
        return published

    async def run_forever(self, interval_seconds: float, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                count = await self.run_once()
                if count:
                    log.info("outbox_relayed", count=count)
            except Exception:
                log.exception("outbox_relay_error")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
