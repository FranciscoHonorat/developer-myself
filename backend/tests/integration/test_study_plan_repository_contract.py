"""Suíte de CONTRATO: a mesma bateria roda no fake e no Mongo (Liskov verificado, ADR-0003)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker

from developer_myself.learning.adapters.memory.repository import InMemoryStudyPlanRepository
from developer_myself.learning.adapters.mongo.repository import MongoStudyPlanRepository, upcast
from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.repository import StudyPlanRepository
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    ContentKind,
    Evidence,
    LearnerId,
    MasteryLevel,
    Notes,
    QuestionSource,
    RecallQuestion,
    Timezone,
    Title,
)
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
NOTES = Notes("a" * 20, "b" * 20, "c" * 20)


@pytest.fixture(
    params=["memory", pytest.param("mongo", marks=[pytest.mark.integration, requires_docker])]
)
async def repository(request: pytest.FixtureRequest) -> AsyncIterator[StudyPlanRepository]:
    if request.param == "memory":
        yield InMemoryStudyPlanRepository()
        return
    url: str = request.getfixturevalue("mongo_url")  # fixture síncrona (sobe o container)
    client = make_client(url)
    name = f"contract_{uuid.uuid4().hex[:12]}"
    db: AsyncDatabase[Doc] = client[name]
    await ensure_schema(db)
    yield MongoStudyPlanRepository(db.study_plans)
    await client.drop_database(name)
    await client.close()


def rich_plan() -> StudyPlan:
    plan = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))
    a = plan.add_content(ContentId.new(), Title("Clean Code"), ContentKind.BOOK, NOW)
    plan.add_content(ContentId.new(), Title("Refactoring"), ContentKind.COURSE, NOW)
    plan.start_session(a.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30))
    ch = plan.add_challenge(a.id, ChallengeId.new(), "Refatorar", MasteryLevel.INTERMEDIATE, NOW)
    plan.solve_challenge(a.id, ch.id, Evidence("https://github.com/x"), NOW)
    plan.add_challenge(a.id, ChallengeId.new(), "Outro", MasteryLevel.ADVANCED, NOW)
    plan.start_session(a.id, NOW + timedelta(hours=1))
    return plan


def review_plan() -> StudyPlan:
    """Revisão ativa com teste de memória e um "preciso revisar" guardado."""
    plan = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))
    a = plan.add_content(ContentId.new(), Title("Clean Code"), ContentKind.BOOK, NOW)
    plan.start_session(a.id, NOW)
    plan.finish_session(Notes("a", "b", "CQS\n- nomes"), NOW + timedelta(minutes=30))
    a._consolidate(NOW)
    questions = (
        RecallQuestion(uuid.uuid7(), "Explique sem consultar: CQS", QuestionSource.TO_REVIEW,
                       "explain_to_review", "CQS"),
        RecallQuestion(uuid.uuid7(), "O que você lembra de nomes?", QuestionSource.SPACED_TOPIC,
                       "recall_topic", "nomes"),
        RecallQuestion(uuid.uuid7(), "Explique funções para quem está começando.",
                       QuestionSource.TOPIC, "teach_beginner", None),
    )  # fmt: skip
    plan.start_session(a.id, NOW + timedelta(days=1), questions)
    return plan


async def test_roundtrip_preserves_the_recall_test(repository: StudyPlanRepository) -> None:
    plan = review_plan()
    await repository.save(plan)
    loaded = await repository.get(plan.id)
    assert loaded is not None
    assert loaded.active_session == plan.active_session
    assert loaded.active_session is not None
    assert len(loaded.active_session.questions) == 3
    assert loaded.contents[0].last_to_review == "CQS\n- nomes"
    assert loaded.contents == plan.contents


def test_upcast_v3_to_v4() -> None:
    doc = {
        "schema_version": 3,
        "active_session": {"content_id": uuid.uuid4(), "started_at": NOW},
        "contents": [{"id": uuid.uuid4()}, {"id": uuid.uuid4()}],
    }
    out = upcast(doc)
    assert out["schema_version"] == 4
    assert out["active_session"]["questions"] == []
    assert [c["last_to_review"] for c in out["contents"]] == [None, None]


def test_upcast_v3_to_v4_without_active_session() -> None:
    out = upcast({"schema_version": 3, "active_session": None, "contents": []})
    assert out["schema_version"] == 4
    assert out["active_session"] is None


async def test_get_missing_returns_none(repository: StudyPlanRepository) -> None:
    assert await repository.get(LearnerId.new()) is None


async def test_roundtrip_preserves_the_whole_aggregate(repository: StudyPlanRepository) -> None:
    plan = rich_plan()
    await repository.save(plan)
    loaded = await repository.get(plan.id)
    assert loaded is not None
    assert loaded.contents == plan.contents
    assert loaded.active_session == plan.active_session
    assert loaded.timezone == plan.timezone
    assert loaded.last_review_on == plan.last_review_on
    assert loaded.version == plan.version == 1
    assert loaded.pending_events == ()


async def test_save_increments_version(repository: StudyPlanRepository) -> None:
    plan = rich_plan()
    await repository.save(plan)
    plan.finish_session(NOTES, NOW + timedelta(hours=1, minutes=30))
    await repository.save(plan)
    loaded = await repository.get(plan.id)
    assert loaded is not None
    assert loaded.version == 2
    assert loaded.active_session is None
    assert loaded.contents[0].points.value == 2


async def test_optimistic_lock_rejects_stale_write(repository: StudyPlanRepository) -> None:
    plan = rich_plan()
    await repository.save(plan)
    tab1 = await repository.get(plan.id)
    tab2 = await repository.get(plan.id)
    assert tab1 is not None
    assert tab2 is not None
    tab1.finish_session(NOTES, NOW + timedelta(hours=1, minutes=30))
    tab2.finish_session(NOTES, NOW + timedelta(hours=1, minutes=30))
    await repository.save(tab1)
    with pytest.raises(ConcurrencyError):
        await repository.save(tab2)


async def test_creating_twice_is_a_conflict(repository: StudyPlanRepository) -> None:
    learner = LearnerId.new()
    await repository.save(StudyPlan.create(learner, Timezone("UTC")))
    with pytest.raises(ConcurrencyError):
        await repository.save(StudyPlan.create(learner, Timezone("UTC")))


async def test_delete(repository: StudyPlanRepository) -> None:
    plan = rich_plan()
    await repository.save(plan)
    await repository.delete(plan.id)
    assert await repository.get(plan.id) is None
