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
    LearnerQuestion,
    MasteryLevel,
    Notes,
    Purpose,
    QuestionSource,
    RecallQuestion,
    StudyPreferences,
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
    a = plan.add_content(
        ContentId.new(),
        Title("Clean Code"),
        ContentKind.BOOK,
        NOW,
        purpose=Purpose("Escrever código limpo"),
    )
    plan.change_purpose(Purpose("Dominar engenharia de software"), NOW)
    plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=2)
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
    a = plan.add_content(
        ContentId.new(),
        Title("Clean Code"),
        ContentKind.BOOK,
        NOW,
        purpose=Purpose("Escrever código limpo"),
    )
    plan.change_purpose(Purpose("Dominar engenharia de software"), NOW)
    plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=2)
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


def warmup_plan() -> StudyPlan:
    """Aquecimento ativo com pergunta do aprendiz, um aquecimento já feito e fila de perguntas."""
    plan = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))
    a = plan.add_content(
        ContentId.new(),
        Title("Clean Code"),
        ContentKind.BOOK,
        NOW,
        purpose=Purpose("Escrever código limpo"),
    )
    plan.change_purpose(Purpose("Dominar engenharia de software"), NOW)
    plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=2)
    plan.start_session(a.id, NOW)
    lq = LearnerQuestion(uuid.uuid7(), "O que é CQS?", NOW, "Separar comando de consulta")
    plan.finish_session(NOTES, NOW + timedelta(minutes=30), future_question=lq)
    plan.last_warmup_on = (NOW - timedelta(days=1)).date()
    questions = (
        RecallQuestion(lq.id, lq.text, QuestionSource.LEARNER, "learner_question",
                       expected_answer=lq.answer),
        RecallQuestion(uuid.uuid7(), "O que você lembra de nomes?", QuestionSource.SPACED_TOPIC,
                       "recall_topic", "nomes"),
    )  # fmt: skip
    plan.start_warmup(a.id, questions, NOW + timedelta(days=1))
    return plan


async def test_roundtrip_preserves_the_warmup(repository: StudyPlanRepository) -> None:
    plan = warmup_plan()
    await repository.save(plan)
    loaded = await repository.get(plan.id)
    assert loaded is not None
    assert loaded.active_warmup == plan.active_warmup
    assert loaded.active_warmup is not None
    assert loaded.active_warmup.questions[0].expected_answer == "Separar comando de consulta"
    assert loaded.last_warmup_on == plan.last_warmup_on
    assert loaded.contents[0].learner_questions == plan.contents[0].learner_questions
    assert len(loaded.contents[0].learner_questions) == 1
    assert loaded.contents == plan.contents


def test_upcast_v5_to_v6() -> None:
    doc = {"schema_version": 5, "contents": [{"id": uuid.uuid4()}]}
    out = upcast(doc)
    assert out["schema_version"] == 6
    assert out["purpose"] is None
    assert out["max_in_progress"] is None
    assert out["contents"][0]["purpose"] is None


def test_upcast_v4_to_v5() -> None:
    doc = {
        "schema_version": 4,
        "active_session": {"content_id": uuid.uuid4(), "started_at": NOW, "questions": [{}]},
        "contents": [{"id": uuid.uuid4()}],
    }
    out = upcast(doc)
    assert out["schema_version"] == 6
    assert out["active_warmup"] is None
    assert out["last_warmup_on"] is None
    assert out["contents"][0]["learner_questions"] == []
    assert out["active_session"]["questions"] == [{"expected_answer": None}]


def test_upcast_v3_to_v4() -> None:
    doc = {
        "schema_version": 3,
        "active_session": {"content_id": uuid.uuid4(), "started_at": NOW},
        "contents": [{"id": uuid.uuid4()}, {"id": uuid.uuid4()}],
    }
    out = upcast(doc)
    assert out["schema_version"] == 6
    assert out["active_session"]["questions"] == []
    assert [c["last_to_review"] for c in out["contents"]] == [None, None]


def test_upcast_v3_to_v4_without_active_session() -> None:
    out = upcast({"schema_version": 3, "active_session": None, "contents": []})
    assert out["schema_version"] == 6
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
    assert loaded.purpose == plan.purpose == Purpose("Dominar engenharia de software")
    assert loaded.max_in_progress == plan.max_in_progress == 2
    assert loaded.contents[0].purpose == Purpose("Escrever código limpo")
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


async def test_content_counts_batches_learners(repository: StudyPlanRepository) -> None:
    p1 = rich_plan()  # 2 conteúdos
    p2 = StudyPlan.create(LearnerId.new(), Timezone("UTC"))  # 0 conteúdos
    missing = LearnerId.new()
    await repository.save(p1)
    await repository.save(p2)
    assert await repository.content_counts([p1.id, p2.id, missing]) == {p1.id: 2, p2.id: 0}
    assert await repository.content_counts([]) == {}
