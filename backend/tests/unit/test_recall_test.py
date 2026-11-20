"""Teste de memória na revisão: perguntas, respostas e o "preciso revisar"."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.errors import InvalidValueError, RecallTestRequiredError
from developer_myself.learning.domain.events import StudySessionFinished
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    LearnerId,
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
LATER = NOW + timedelta(minutes=30)
NOTES = Notes("a" * 20, "b" * 20, "c" * 20)


def question(text: str = "O que você lembra de canais?") -> RecallQuestion:
    return RecallQuestion(
        id=uuid.uuid7(),
        text=text,
        source=QuestionSource.TOPIC,
        template="recall_topic",
        topic="canais",
    )


QUESTIONS = (question("P1"), question("P2"), question("P3"))


def answers(
    qs: tuple[RecallQuestion, ...] = QUESTIONS, grade: RecallGrade = RecallGrade.MISSED
) -> tuple[RecallAnswer, ...]:
    return tuple(RecallAnswer(question_id=q.id, answer="não lembrei", grade=grade) for q in qs)


@pytest.fixture
def plan() -> StudyPlan:
    return StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))


def add(plan: StudyPlan, title: str = "Clean Code") -> Content:
    return plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)


def consolidated(plan: StudyPlan) -> Content:
    content = add(plan)
    content._consolidate()
    return content


# ---------------------------------------------------------------- value objects
def test_question_text_must_not_be_blank() -> None:
    with pytest.raises(InvalidValueError):
        question("   ")


def test_question_text_over_500_is_refused() -> None:
    question("a" * 500)
    with pytest.raises(InvalidValueError):
        question("a" * 501)


def test_question_topic_over_500_is_refused() -> None:
    with pytest.raises(InvalidValueError):
        RecallQuestion(uuid.uuid7(), "P", QuestionSource.TO_REVIEW, "explain_to_review", "a" * 501)


def test_answer_over_5000_is_refused() -> None:
    RecallAnswer(uuid.uuid7(), "a" * 5000, RecallGrade.RECALLED)
    with pytest.raises(InvalidValueError):
        RecallAnswer(uuid.uuid7(), "a" * 5001, RecallGrade.RECALLED)


# ---------------------------------------------------------------- iniciar
def test_review_start_keeps_the_questions(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    assert plan.active_session is not None
    assert plan.active_session.questions == QUESTIONS


def test_study_start_ignores_questions(plan: StudyPlan) -> None:
    content = add(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    assert plan.active_session is not None
    assert plan.active_session.questions == ()


# ---------------------------------------------------------------- finalizar
def test_finish_review_without_answers_is_refused(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    with pytest.raises(RecallTestRequiredError):
        plan.finish_session(NOTES, LATER, RecallRating.GOOD)
    assert plan.active_session is not None


def test_expired_review_is_abandoned_without_test_or_rating(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    outcome = plan.finish_session(NOTES, NOW + timedelta(hours=5))
    assert outcome.awarded is False
    assert plan.active_session is None


def test_finish_with_missing_answer_is_refused(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    with pytest.raises(RecallTestRequiredError):
        plan.finish_session(NOTES, LATER, RecallRating.GOOD, answers(QUESTIONS[:2]))


def test_finish_with_unknown_question_id_is_refused(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    wrong = (*answers(QUESTIONS[:2]), RecallAnswer(uuid.uuid7(), "", RecallGrade.MISSED))
    with pytest.raises(RecallTestRequiredError):
        plan.finish_session(NOTES, LATER, RecallRating.GOOD, wrong)


def test_finish_with_duplicated_answer_is_refused(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    dup = (*answers(QUESTIONS), *answers(QUESTIONS[:1]))
    with pytest.raises(RecallTestRequiredError):
        plan.finish_session(NOTES, LATER, RecallRating.GOOD, dup)


def test_finish_with_all_missed_still_awards_when_rules_met(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    outcome = plan.finish_session(NOTES, LATER, RecallRating.FORGOT, answers())
    assert outcome.awarded


def test_finish_without_questions_needs_no_test(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW)
    outcome = plan.finish_session(NOTES, LATER, RecallRating.GOOD)
    assert outcome.awarded


def test_event_carries_the_recall_test(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW, QUESTIONS)
    given = (
        RecallAnswer(QUESTIONS[0].id, "r0", RecallGrade.MISSED, useful=True),
        RecallAnswer(QUESTIONS[1].id, "r1", RecallGrade.PARTIAL, useful=False),
        RecallAnswer(QUESTIONS[2].id, "r2", RecallGrade.RECALLED),
    )
    # A ordem das respostas não importa: o evento segue a ordem das perguntas.
    plan.finish_session(NOTES, LATER, RecallRating.GOOD, tuple(reversed(given)))
    finished = next(e for e in plan.pull_events() if isinstance(e, StudySessionFinished))
    items = envelope(finished)["payload"]["recall_test"]
    assert [i["position"] for i in items] == [0, 1, 2]
    assert items[0] == {
        "question_id": str(QUESTIONS[0].id),
        "text": "P1",
        "source": "TOPIC",
        "template": "recall_topic",
        "topic": "canais",
        "position": 0,
        "answer": "r0",
        "grade": "MISSED",
        "useful": True,
    }
    assert [i["grade"] for i in items] == ["MISSED", "PARTIAL", "RECALLED"]
    assert [i["useful"] for i in items] == [True, False, None]


def test_study_event_has_no_recall_test(plan: StudyPlan) -> None:
    content = add(plan)
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, LATER)
    finished = next(e for e in plan.pull_events() if isinstance(e, StudySessionFinished))
    assert finished.recall_test == ()


# ---------------------------------------------------------------- preciso revisar
def test_finish_updates_last_to_review(plan: StudyPlan) -> None:
    content = add(plan)
    assert content.last_to_review is None
    plan.start_session(content.id, NOW)
    plan.finish_session(Notes("a", "b", "goroutines"), NOW + timedelta(minutes=5))
    assert content.last_to_review == "goroutines"


def test_blank_to_review_keeps_previous(plan: StudyPlan) -> None:
    content = add(plan)
    plan.start_session(content.id, NOW)
    plan.finish_session(Notes("a", "b", "goroutines"), LATER)
    plan.start_session(content.id, LATER)
    plan.finish_session(Notes("a", "b", "   "), LATER + timedelta(minutes=30))
    assert content.last_to_review == "goroutines"


def test_backfill_sets_only_when_empty(plan: StudyPlan) -> None:
    content = add(plan)
    assert not plan.backfill_last_to_review(content.id, "  ")
    assert plan.backfill_last_to_review(content.id, "canais")
    assert content.last_to_review == "canais"
    assert not plan.backfill_last_to_review(content.id, "select")
    assert content.last_to_review == "canais"


def test_answers_without_questions_are_ignored(plan: StudyPlan) -> None:
    content = consolidated(plan)
    plan.start_session(content.id, NOW)
    outcome = plan.finish_session(NOTES, LATER, RecallRating.GOOD, answers())
    assert outcome.awarded
