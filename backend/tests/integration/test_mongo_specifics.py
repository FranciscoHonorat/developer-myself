"""O que é específico do Mongo: outbox no mesmo documento e `$jsonSchema`."""

import dataclasses
import uuid

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import WriteError
from tests.integration.conftest import requires_docker
from tests.integration.test_study_plan_repository_contract import rich_plan

from developer_myself.learning.adapters.mongo.outbox_relay import OutboxRelay
from developer_myself.learning.adapters.mongo.repository import MongoStudyPlanRepository
from developer_myself.shared.adapters.mongo_setup import Doc

pytestmark = [pytest.mark.integration, requires_docker]


async def test_events_go_to_the_outbox_in_the_same_write(mongo_db: AsyncDatabase[Doc]) -> None:
    repo = MongoStudyPlanRepository(mongo_db.study_plans)
    plan = rich_plan()
    expected = [e.type_name() for e in plan.pending_events]
    await repo.save(plan)
    doc = await mongo_db.study_plans.find_one({"_id": plan.id.value})
    assert doc is not None
    assert doc["has_outbox"] is True
    assert [e["type"] for e in doc["outbox"]] == expected


async def test_relay_publishes_then_pulls(mongo_db: AsyncDatabase[Doc]) -> None:
    repo = MongoStudyPlanRepository(mongo_db.study_plans)
    plan = rich_plan()
    await repo.save(plan)
    published: list[dict[str, object]] = []

    async def publish(envelope: dict[str, object]) -> None:
        published.append(envelope)

    relay = OutboxRelay(mongo_db.study_plans, publish)
    count = await relay.run_once()
    assert count == len(published) > 0
    assert all(isinstance(e["event_id"], str) for e in published)
    doc = await mongo_db.study_plans.find_one({"_id": plan.id.value})
    assert doc is not None
    assert doc["outbox"] == []
    assert doc["has_outbox"] is False
    assert await relay.run_once() == 0


async def test_relay_keeps_events_when_broker_fails(mongo_db: AsyncDatabase[Doc]) -> None:
    repo = MongoStudyPlanRepository(mongo_db.study_plans)
    plan = rich_plan()
    total = len(plan.pending_events)
    await repo.save(plan)

    async def broken(_: dict[str, object]) -> None:
        raise ConnectionError("broker fora do ar")

    assert await OutboxRelay(mongo_db.study_plans, broken).run_once() == 0
    doc = await mongo_db.study_plans.find_one({"_id": plan.id.value})
    assert doc is not None
    assert len(doc["outbox"]) == total
    assert doc["has_outbox"] is True


async def test_json_schema_rejects_malformed_document(mongo_db: AsyncDatabase[Doc]) -> None:
    with pytest.raises(WriteError):
        await mongo_db.study_plans.insert_one({"_id": uuid.uuid4(), "contents": "não é lista"})


async def test_v1_document_is_upcast_on_read_and_saved_as_current(
    mongo_db: AsyncDatabase[Doc],
) -> None:
    """Migração lazy (ADR-0005): um documento antigo continua legível e é regravado em v2."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from developer_myself.learning.domain.value_objects import LearnerId  # noqa: PLC0415

    learner, content = uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 11, 1, tzinfo=UTC)
    await mongo_db.study_plans.insert_one({
        "_id": learner, "schema_version": 1, "version": 3, "timezone": "UTC",
        "last_review_on": None, "active_session": None, "outbox": [], "has_outbox": False,
        "contents": [{
            "id": content, "title": "Antigo", "kind": "BOOK", "status": "IN_PROGRESS",
            "points": 2, "queued_at": now, "last_session_at": now, "finished_at": None,
            "challenges": [],
        }],
    })  # fmt: skip
    repo = MongoStudyPlanRepository(mongo_db.study_plans)
    plan = await repo.get(LearnerId(learner))
    assert plan is not None
    assert plan.contents[0].session_count == 1
    assert plan.contents[0].first_session_at == now
    await repo.save(plan)
    doc = await mongo_db.study_plans.find_one({"_id": learner})
    assert doc is not None
    assert doc["schema_version"] == 6  # v1 -> v2 -> v3 -> v4 -> v5 -> v6 (SDT)
    assert doc["contents"][0]["review_count"] == 0
    assert doc["preferences"] == {"minutes_per_day": 210, "rest_days": []}
    assert plan.preferences.minutes_per_day == 210


async def test_model_registry_keeps_history_and_one_active(mongo_db: AsyncDatabase[Doc]) -> None:
    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    from developer_myself.insights.adapters.mongo.model_registry import (  # noqa: PLC0415
        MongoModelRegistry,
    )
    from developer_myself.insights.application.model_registry import StoredModel  # noqa: PLC0415

    registry = MongoModelRegistry(mongo_db.ml_models)
    t = datetime(2026, 11, 1, tzinfo=UTC)
    assert await registry.active() is None
    await registry.publish(StoredModel("a", t, True, {"metadata": {"v": 1}}))
    await registry.publish(StoredModel("b", t + timedelta(hours=1), False, {"metadata": {}}))
    await registry.publish(StoredModel("c", t + timedelta(hours=2), True, {"metadata": {}}))
    active = await registry.active()
    assert active is not None
    assert active.id == "c"
    assert await mongo_db.ml_models.count_documents({"active": True}) == 1
    assert [m.id for m in await registry.recent()] == ["c", "b", "a"]


async def test_labeled_reviews_query(mongo_db: AsyncDatabase[Doc]) -> None:
    from tests.unit.test_neural import record  # noqa: PLC0415

    from developer_myself.insights.adapters.mongo.store import (  # noqa: PLC0415
        MongoSessionHistoryStore,
    )

    store = MongoSessionHistoryStore(mongo_db.study_sessions, mongo_db.processed_events)
    await store.record(record(1, rating=3))
    await store.record(dataclasses.replace(record(2, rating=3), recall_rating=None))
    labeled = await store.labeled_reviews()
    assert [r.event_id for r in labeled] == ["e1"]
    assert labeled[0].last_contact_days == 10.0
