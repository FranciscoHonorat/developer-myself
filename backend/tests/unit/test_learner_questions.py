"""Perguntas para o "eu do futuro": escritas no fim do estudo, voltam no teste de memória."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.learning.domain.content import MAX_LEARNER_QUESTIONS, Content
from developer_myself.learning.domain.errors import InvalidValueError, RecallTestRequiredError
from developer_myself.learning.domain.events import StudySessionFinished
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
    RecallRating,
    Timezone,
    Title,
)
from developer_myself.shared.events import envelope

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
NOTES = Notes("a" * 20, "b" * 20, "c" * 20)


@pytest.fixture
def plan() -> StudyPlan:
    return StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))


def add(plan: StudyPlan, title: str = "Clean Code") -> Content:
    return plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)


def lq(text: str = "O que é CQS?", answer: str | None = None) -> LearnerQuestion:
    return LearnerQuestion(id=uuid.uuid7(), text=text, created_at=NOW, answer=answer)


def study(plan: StudyPlan, content: Content, minutes: int, q: LearnerQuestion | None) -> None:
    start = NOW + timedelta(days=content.session_count)
    plan.start_session(content.id, start)
    plan.finish_session(NOTES, start + timedelta(minutes=minutes), future_question=q)


def finished_event(plan: StudyPlan) -> StudySessionFinished:
    return next(e for e in reversed(plan.pull_events()) if isinstance(e, StudySessionFinished))


# ---------------------------------------------------------------- value object
def test_learner_question_text_must_not_be_blank() -> None:
    with pytest.raises(InvalidValueError):
        lq("   ")


def test_learner_question_text_over_500_is_refused() -> None:
    lq("a" * 500)
    with pytest.raises(InvalidValueError):
        lq("a" * 501)


def test_learner_answer_over_2000_is_refused() -> None:
    lq(answer="a" * 2000)
    with pytest.raises(InvalidValueError):
        lq(answer="a" * 2001)


def test_blank_learner_answer_becomes_none() -> None:
    assert lq(answer="   ").answer is None


def test_recall_question_has_no_expected_answer_by_default() -> None:
    q = RecallQuestion(uuid.uuid7(), "P", QuestionSource.TOPIC, "recall_topic")
    assert q.expected_answer is None


# ---------------------------------------------------------------- estudo
def test_study_session_keeps_future_question(plan: StudyPlan) -> None:
    content = add(plan)
    study(plan, content, 25, lq("O que é CQS?", "Separar comando de consulta"))
    assert content.learner_questions[-1].text == "O que é CQS?"
    event = finished_event(plan)
    assert event.future_question is not None
    assert event.future_question["text"] == "O que é CQS?"
    assert event.future_question["answer"] == "Separar comando de consulta"
    payload = envelope(event)["payload"]["future_question"]
    assert payload["text"] == "O que é CQS?"


def test_unscored_study_still_keeps_future_question(plan: StudyPlan) -> None:
    content = add(plan)
    study(plan, content, 24, lq())
    assert len(content.learner_questions) == 1


def test_study_without_future_question_has_none_in_event(plan: StudyPlan) -> None:
    content = add(plan)
    study(plan, content, 25, None)
    assert content.learner_questions == ()
    assert finished_event(plan).future_question is None


def test_expired_study_does_not_keep_future_question(plan: StudyPlan) -> None:
    content = add(plan)
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(hours=5), future_question=lq())
    assert content.learner_questions == ()


def test_learner_questions_keep_only_five_newest(plan: StudyPlan) -> None:
    content = add(plan)
    for i in range(1, 7):
        study(plan, content, 25, lq(f"q{i}"))
    assert MAX_LEARNER_QUESTIONS == 5
    assert tuple(q.text for q in content.learner_questions) == ("q2", "q3", "q4", "q5", "q6")


# ---------------------------------------------------------------- revisão
def consolidated_with(plan: StudyPlan, *questions: LearnerQuestion) -> Content:
    content = add(plan)
    for q in questions:
        content._add_learner_question(q)
    content._consolidate()
    return content


def test_review_ignores_future_question(plan: StudyPlan) -> None:
    content = consolidated_with(plan)
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.GOOD, future_question=lq())
    assert content.learner_questions == ()


def test_review_consumes_learner_questions_it_asked(plan: StudyPlan) -> None:
    asked, kept = lq("asked"), lq("kept")
    content = consolidated_with(plan, asked, kept)
    questions = (
        RecallQuestion(asked.id, asked.text, QuestionSource.LEARNER, "learner_question"),
        RecallQuestion(uuid.uuid7(), "P2", QuestionSource.TOPIC, "recall_topic", "x"),
    )
    plan.start_session(content.id, NOW, questions)
    graded = tuple(RecallAnswer(q.id, "", RecallGrade.RECALLED) for q in questions)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.GOOD, graded)
    assert content.learner_questions == (kept,)


def test_test_message_uses_real_question_count(plan: StudyPlan) -> None:
    content = consolidated_with(plan)
    questions = tuple(
        RecallQuestion(uuid.uuid7(), f"P{i}", QuestionSource.TOPIC, "recall_topic") for i in (1, 2)
    )
    plan.start_session(content.id, NOW, questions)
    with pytest.raises(RecallTestRequiredError, match="as 2 perguntas"):
        plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.GOOD)
