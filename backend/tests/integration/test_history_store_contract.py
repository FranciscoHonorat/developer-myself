"""Contrato da paginação do histórico: a mesma bateria roda no fake e no Mongo (ADR-0003)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker

from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.adapters.mongo.store import MongoSessionHistoryStore
from developer_myself.insights.application.history import (
    HistoryCursor,
    SessionHistoryStore,
    SessionRecord,
)
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client

NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)
ME, OTHER = str(uuid.uuid7()), str(uuid.uuid7())


def record(event_id: str, minutes: int, learner: str = ME) -> SessionRecord:
    at = NOW + timedelta(minutes=minutes)
    return SessionRecord(
        event_id=event_id,
        learner_id=learner,
        type="study_session_finished",
        content_id=str(uuid.uuid7()),
        content_title="x",
        kind="STUDY",
        started_at=at - timedelta(minutes=25),
        finished_at=at,
        duration_seconds=1_500,
        awarded=True,
        reason=None,
        notes_studied="",
        notes_understood="",
        notes_to_review="",
        level_after=None,
    )


@pytest.fixture(
    params=["memory", pytest.param("mongo", marks=[pytest.mark.integration, requires_docker])]
)
async def store(request: pytest.FixtureRequest) -> AsyncIterator[SessionHistoryStore]:
    if request.param == "memory":
        yield InMemorySessionHistoryStore()
        return
    url: str = request.getfixturevalue("mongo_url")
    client = make_client(url)
    name = f"contract_hist_{uuid.uuid4().hex[:12]}"
    db: AsyncDatabase[Doc] = client[name]
    await ensure_schema(db)
    yield MongoSessionHistoryStore(db.study_sessions, db.processed_events)
    await client.drop_database(name)
    await client.close()


async def ids(store: SessionHistoryStore, limit: int, after: HistoryCursor | None) -> list[str]:
    return [r.event_id for r in await store.page_for(ME, limit, after)]


async def test_pages_walk_newest_first_breaking_ties_by_event_id(
    store: SessionHistoryStore,
) -> None:
    # "b" e "c" terminaram no mesmo instante: o event_id decide a ordem, sem pular nenhum.
    for r in (record("a", 0), record("b", 10), record("c", 10), record("d", 20)):
        await store.record(r)
    await store.record(record("z", 30, learner=OTHER))

    first = await store.page_for(ME, 2)
    assert [r.event_id for r in first] == ["d", "c"]
    assert await ids(store, 2, HistoryCursor.of(first[-1])) == ["b", "a"]


async def test_page_after_the_last_item_is_empty(store: SessionHistoryStore) -> None:
    await store.record(record("a", 0))
    assert await ids(store, 5, HistoryCursor(NOW, "a")) == []


async def test_summaries_for_batches_counts_and_last_activity(store: SessionHistoryStore) -> None:
    await store.record(record("a", 5, learner=ME))
    await store.record(record("b", 20, learner=ME))
    await store.record(record("c", 10, learner=OTHER))
    summaries = await store.summaries_for([ME, OTHER, str(uuid.uuid7())])
    assert summaries[ME].sessions == 2
    assert summaries[ME].last_activity_at == NOW + timedelta(minutes=20)
    assert summaries[OTHER].sessions == 1
    assert summaries[OTHER].last_activity_at == NOW + timedelta(minutes=10)
    assert len(summaries) == 2
    assert await store.summaries_for([]) == {}
