"""Aquecimento: 2 perguntas sem consultar, fora de sessão, sem ponto, 1 por dia."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.errors import (
    ContentHasProgressError,
    NoActiveWarmupError,
    NothingToWarmUpError,
    RecallTestRequiredError,
    SessionAlreadyActiveError,
    WarmupAlreadyDoneError,
)
from developer_myself.learning.domain.events import PointAwarded, WarmupFinished
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    LearnerId,
    LearnerQuestion,
    Notes,
    QuestionSource,
    RecallAnswer,
    RecallGrade,
    RecallQuestion,
    Timezone,
    Title,
)
from developer_myself.shared.events import envelope

# 12:00 UTC = 09:00 em São Paulo
NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
NOTES = Notes("a" * 20, "b" * 20, "c" * 20)


def q(
    text: str, source: QuestionSource = QuestionSource.TOPIC, qid: uuid.UUID | None = None
) -> RecallQuestion:
    return RecallQuestion(qid or uuid.uuid7(), text, source, "recall_topic", "t")


QUESTIONS = (q("P1"), q("P2"))


def graded(qs: tuple[RecallQuestion, ...] = QUESTIONS) -> tuple[RecallAnswer, ...]:
    return tuple(RecallAnswer(x.id, "lembrei", RecallGrade.RECALLED) for x in qs)


@pytest.fixture
def plan() -> StudyPlan:
    return StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))


def add(plan: StudyPlan, title: str = "Clean Code") -> Content:
    return plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)


def studied(plan: StudyPlan, title: str = "Clean Code") -> Content:
    """Conteúdo em andamento com 1 sessão finalizada, terminada antes de NOW."""
    content = add(plan, title)
    start = NOW - timedelta(days=1)
    plan.start_session(content.id, start)
    plan.finish_session(NOTES, start + timedelta(minutes=25))
    plan.pull_events()
    return content


# ---------------------------------------------------------------- iniciar
def test_start_returns_given_questions(plan: StudyPlan) -> None:
    content = studied(plan)
    warmup = plan.start_warmup(content.id, QUESTIONS, NOW)
    assert warmup.questions == QUESTIONS
    assert warmup.content_id == content.id
    assert plan.current_warmup(NOW) == warmup
    assert plan.pull_events() == []


def test_start_again_returns_same_warmup(plan: StudyPlan) -> None:
    content = studied(plan)
    first = plan.start_warmup(content.id, QUESTIONS, NOW)
    again = plan.start_warmup(content.id, (q("outra"), q("mais")), NOW + timedelta(minutes=1))
    assert again == first


def test_start_refused_with_active_session(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_session(content.id, NOW)
    with pytest.raises(SessionAlreadyActiveError):
        plan.start_warmup(content.id, QUESTIONS, NOW)


def test_start_refused_after_done_today(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    plan.finish_warmup(graded(), NOW + timedelta(minutes=2))
    assert plan.warmed_up_today(NOW + timedelta(hours=1))
    with pytest.raises(WarmupAlreadyDoneError):
        plan.start_warmup(content.id, QUESTIONS, NOW + timedelta(hours=1))


def test_next_local_day_allows_again(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    plan.finish_warmup(graded(), NOW + timedelta(minutes=2))
    tomorrow = NOW + timedelta(days=1)
    assert not plan.warmed_up_today(tomorrow)
    plan.start_warmup(content.id, QUESTIONS, tomorrow)


def test_content_without_finished_session_is_not_eligible(plan: StudyPlan) -> None:
    content = add(plan)
    assert not plan.can_warm_up(content)
    with pytest.raises(NothingToWarmUpError):
        plan.start_warmup(content.id, QUESTIONS, NOW)


def test_locked_content_is_not_eligible(plan: StudyPlan) -> None:
    studied(plan)
    locked = add(plan, "Refactoring")
    locked.session_count = 1  # atalho: em produção um bloqueado nunca teve sessão
    assert not plan.can_warm_up(locked)
    with pytest.raises(NothingToWarmUpError):
        plan.start_warmup(locked.id, QUESTIONS, NOW)


def test_studied_content_is_eligible(plan: StudyPlan) -> None:
    assert plan.can_warm_up(studied(plan))


# ---------------------------------------------------------------- concluir
def test_finish_requires_every_answer(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    with pytest.raises(RecallTestRequiredError, match="as 2 perguntas"):
        plan.finish_warmup(graded(QUESTIONS[:1]), NOW + timedelta(minutes=2))
    assert plan.current_warmup(NOW) is not None


def test_finish_records_event_and_awards_nothing(plan: StudyPlan) -> None:
    content = studied(plan)
    points = content.points
    plan.start_warmup(content.id, QUESTIONS, NOW)
    finished_id = plan.finish_warmup(graded(), NOW + timedelta(minutes=2))
    assert finished_id == content.id
    assert content.points == points
    assert plan.active_warmup is None
    events = plan.pull_events()
    assert not any(isinstance(e, PointAwarded) for e in events)
    (event,) = events
    assert isinstance(event, WarmupFinished)
    assert event.content_id == content.id.value
    assert event.content_title == "Clean Code"
    assert event.duration_seconds == 120
    assert [item["text"] for item in event.recall_test] == ["P1", "P2"]
    assert envelope(event)["type"] == "warmup_finished"


def test_finish_consumes_learner_question(plan: StudyPlan) -> None:
    content = studied(plan)
    asked = LearnerQuestion(uuid.uuid7(), "O que é CQS?", NOW)
    kept = LearnerQuestion(uuid.uuid7(), "E SRP?", NOW)
    content._add_learner_question(asked)
    content._add_learner_question(kept)
    questions = (q(asked.text, QuestionSource.LEARNER, asked.id), q("P2"))
    plan.start_warmup(content.id, questions, NOW)
    plan.finish_warmup(graded(questions), NOW + timedelta(minutes=2))
    assert content.learner_questions == (kept,)


def test_finish_across_midnight_counts_for_start_day(plan: StudyPlan) -> None:
    content = studied(plan)
    start = datetime(2026, 11, 3, 2, 58, tzinfo=UTC)  # 23:58 de 02/11 em São Paulo
    plan.start_warmup(content.id, QUESTIONS, start)
    plan.finish_warmup(graded(), start + timedelta(minutes=4))  # 00:02 de 03/11
    assert plan.last_warmup_on == plan.timezone.local_date(start)
    assert not plan.warmed_up_today(start + timedelta(hours=10))


def test_finish_after_4h_raises_and_clears(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    late = NOW + timedelta(hours=4, minutes=1)
    assert plan.current_warmup(late) is None
    with pytest.raises(NoActiveWarmupError):
        plan.finish_warmup(graded(), late)
    assert plan.active_warmup is None
    assert plan.last_warmup_on is None


def test_finish_without_warmup_raises(plan: StudyPlan) -> None:
    with pytest.raises(NoActiveWarmupError):
        plan.finish_warmup(graded(), NOW)


def test_start_after_4h_replaces_stale_warmup(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    fresh = (q("nova"), q("outra"))
    late = NOW + timedelta(hours=5)
    assert plan.start_warmup(content.id, fresh, late).questions == fresh


# ---------------------------------------------------------------- cancelar
def test_cancel_clears_without_event(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    plan.cancel_warmup(NOW + timedelta(minutes=1))
    assert plan.active_warmup is None
    assert plan.pull_events() == []
    assert not plan.warmed_up_today(NOW)


def test_cancel_without_warmup_raises(plan: StudyPlan) -> None:
    with pytest.raises(NoActiveWarmupError):
        plan.cancel_warmup(NOW)


# ---------------------------------------------------------------- convivência
def test_start_session_discards_active_warmup(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    plan.start_session(content.id, NOW + timedelta(minutes=1))
    assert plan.active_warmup is None
    assert not any(isinstance(e, WarmupFinished) for e in plan.pull_events())


def test_warmed_content_cannot_be_removed(plan: StudyPlan) -> None:
    content = studied(plan)
    plan.start_warmup(content.id, QUESTIONS, NOW)
    with pytest.raises(ContentHasProgressError):
        plan.remove_content(content.id, NOW)
