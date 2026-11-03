"""Outbox → RabbitMQ → consumer → `study_sessions`, de forma idempotente (passo 9)."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta

import aio_pika
import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker
from tests.integration.test_study_plan_repository_contract import NOTES, NOW, rich_plan

from developer_myself.insights.adapters.consumers.session_history import consume_session_history
from developer_myself.insights.adapters.mongo.store import MongoSessionHistoryStore
from developer_myself.insights.application.history import RecordSessionHistory
from developer_myself.learning.adapters.mongo.outbox_relay import OutboxRelay
from developer_myself.learning.adapters.mongo.repository import MongoStudyPlanRepository
from developer_myself.learning.adapters.rabbitmq.publisher import RabbitPublisher
from developer_myself.shared.adapters.mongo_setup import Doc

pytestmark = [pytest.mark.integration, requires_docker]


async def wait_for(predicate: Callable[[], Awaitable[bool]], limit_seconds: float = 10.0) -> None:
    """Polling de um estado externo (banco/broker): não há evento para esperar."""

    async def poll() -> None:
        while not await predicate():  # noqa: ASYNC110 - estado externo
            await asyncio.sleep(0.1)

    await asyncio.wait_for(poll(), limit_seconds)


async def test_finished_session_reaches_history_once(
    mongo_db: AsyncDatabase[Doc], rabbit_url: str
) -> None:
    repo = MongoStudyPlanRepository(mongo_db.study_plans)
    store = MongoSessionHistoryStore(mongo_db.study_sessions, mongo_db.processed_events)
    plan = rich_plan()
    plan.finish_session(NOTES, NOW + timedelta(hours=1, minutes=40))
    await repo.save(plan)

    connection = await aio_pika.connect_robust(rabbit_url)
    try:
        await consume_session_history(connection, RecordSessionHistory(store))
        publisher = await RabbitPublisher.create(connection)
        relay = OutboxRelay(mongo_db.study_plans, publisher.publish)
        await relay.run_once()

        async def two_sessions() -> bool:
            return await mongo_db.study_sessions.count_documents({}) == 2

        await wait_for(two_sessions)

        # At-least-once: republicar o mesmo evento não duplica o histórico.
        records = await store.list_for(str(plan.id), 10)
        duplicate = {
            "event_id": records[0].event_id,
            "type": "study_session_finished",
            "version": 1,
            "learner_id": str(plan.id),
            "occurred_at": records[0].finished_at.isoformat(),
            "correlation_id": None,
            "payload": {
                "content_id": records[0].content_id,
                "content_title": records[0].content_title,
                "kind": records[0].kind,
                "started_at": records[0].started_at.isoformat(),
                "finished_at": records[0].finished_at.isoformat(),
                "duration_seconds": records[0].duration_seconds,
                "notes_studied": "",
                "notes_understood": "",
                "notes_to_review": "",
                "awarded": records[0].awarded,
                "withheld_reason": None,
                "level_after": "BEGINNER",
            },
        }
        await publisher.publish(duplicate)
        await asyncio.sleep(1)
        assert await mongo_db.study_sessions.count_documents({}) == 2
        assert all(r.awarded for r in records)
    finally:
        await connection.close()


async def test_poison_message_goes_to_dlq(rabbit_url: str) -> None:
    connection = await aio_pika.connect_robust(rabbit_url)
    try:

        async def handler(_: dict[str, object]) -> bool:
            return True

        await consume_session_history(connection, handler)
        channel = await connection.channel()
        exchange = await channel.get_exchange("learning.events")
        await exchange.publish(
            aio_pika.Message(body=b"isto nao e json"),
            routing_key="learning.study_session_finished.v1",
        )
        dlq = await channel.get_queue("insights.session-history.dlq")

        async def in_dlq() -> bool:
            message = await dlq.get(fail=False)
            if message is None:
                return False
            await message.ack()
            return message.body == b"isto nao e json"

        await wait_for(in_dlq)
    finally:
        await connection.close()
