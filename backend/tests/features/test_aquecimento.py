"""Steps do aquecimento de recuperação, sobre os casos de uso em memória."""

from dataclasses import dataclass
from datetime import time

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import GOOD_NOTES, World

from developer_myself.insights.application.recommender import SpacedRepetitionRule
from developer_myself.learning.application.use_cases import AnswerInput, FutureQuestionInput
from developer_myself.learning.domain.errors import RecallTestRequiredError
from developer_myself.learning.domain.study_plan import ActiveWarmup
from developer_myself.learning.domain.value_objects import ContentId, SessionKind
from developer_myself.planning.application.warmup import (
    NextStep,
    WarmupStatus,
    next_step,
    warmup_status,
)

scenarios("aquecimento.feature")

RECOMMENDER = SpacedRepetitionRule()


@dataclass
class Warming:
    status: WarmupStatus | None = None
    warmup: ActiveWarmup | None = None
    first: ActiveWarmup | None = None
    next: NextStep | None = None


@pytest.fixture
def warming() -> Warming:
    return Warming()


def status(world: World) -> WarmupStatus:
    return warmup_status(world.plan(), RECOMMENDER, world.clock.now())


def start(world: World, warming: Warming) -> ActiveWarmup:
    target = status(world).target
    assert target is not None, "nada para aquecer"
    warming.warmup = world.run(world.uc.start_warmup(world.learner_id, target.id.value))
    return warming.warmup


def answers(warmup: ActiveWarmup) -> list[AnswerInput]:
    return [AnswerInput(q.id, "lembrei", "RECALLED") for q in warmup.questions]


def finish(world: World, warming: Warming) -> ContentId:
    assert warming.warmup is not None
    done = world.run(world.uc.finish_warmup(world.learner_id, answers(warming.warmup)))
    warming.next = next_step(world.plan(), RECOMMENDER, world.clock.now())
    return done


def study_yesterday(world: World, title: str, question: str | None = None) -> None:
    content = world.content(title)
    world.run(world.uc.start_session(world.learner_id, content.id.value))
    world.clock.advance(minutes=25)
    future = FutureQuestionInput(question) if question is not None else None
    world.run(world.uc.finish_session(world.learner_id, GOOD_NOTES, None, [], future))
    world.clock.set(world.local_moment(time(8, 0), days=1))


# ---------------------------------------------------------------- dado
@given(parsers.parse('que estudei "{title}" ontem'))
def given_studied_yesterday(world: World, title: str) -> None:
    study_yesterday(world, title)


@given(parsers.parse('que estudei "{title}" ontem deixando a pergunta "{question}"'))
def given_studied_with_question(world: World, title: str, question: str) -> None:
    study_yesterday(world, title, question)


@given("que iniciei o aquecimento")
def given_started(world: World, warming: Warming) -> None:
    warming.first = start(world, warming)


@given("que concluí o aquecimento de hoje")
def given_done_today(world: World, warming: Warming) -> None:
    start(world, warming)
    world.clock.advance(minutes=2)
    finish(world, warming)


# ---------------------------------------------------------------- quando
@when("eu abro o aquecimento")
def when_open(world: World, warming: Warming) -> None:
    warming.status = status(world)


@when("eu inicio o aquecimento")
def when_start(world: World, warming: Warming) -> None:
    world.clock.advance(minutes=1)
    start(world, warming)


@when("eu concluo o aquecimento sem corrigir")
def when_finish_ungraded(world: World) -> None:
    world.clock.advance(minutes=2)
    world.attempt(world.uc.finish_warmup(world.learner_id, []))


@when("eu concluo o aquecimento corrigindo tudo")
def when_finish(world: World, warming: Warming) -> None:
    world.clock.advance(minutes=2)
    finish(world, warming)


@when("eu cancelo o aquecimento")
def when_cancel(world: World) -> None:
    world.run(world.uc.cancel_warmup(world.learner_id))


# ---------------------------------------------------------------- então
@then(parsers.parse('o aquecimento está disponível para "{title}"'))
def then_available_for(world: World, warming: Warming, title: str) -> None:
    current = warming.status or status(world)
    assert current.available
    assert current.target is not None
    assert current.target.title.value == title


@then("o aquecimento não está disponível")
def then_unavailable(warming: Warming) -> None:
    assert warming.status is not None
    assert not warming.status.available


@then("o aquecimento de hoje está feito")
def then_done_today(warming: Warming) -> None:
    assert warming.status is not None
    assert warming.status.done_today


@then(parsers.parse("o aquecimento tem {count:d} perguntas"))
def then_question_count(world: World, warming: Warming, count: int) -> None:
    assert len(start(world, warming).questions) == count


@then(parsers.parse('a 1ª pergunta do aquecimento é "{text}"'))
def then_first_question(warming: Warming, text: str) -> None:
    assert warming.warmup is not None
    assert warming.warmup.questions[0].text == text


@then("as perguntas do aquecimento não mudaram")
def then_same_questions(warming: Warming) -> None:
    assert warming.first is not None
    assert warming.warmup == warming.first


@then("a ação é recusada pedindo o teste")
def then_refused_for_test(world: World) -> None:
    assert isinstance(world.error, RecallTestRequiredError)


@then(parsers.parse("o histórico registra um aquecimento com {count:d} perguntas"))
def then_history_has_warmup(world: World, count: int) -> None:
    records = world.run(world.history.list_for(str(world.learner_id), 100))
    (warmup,) = [r for r in records if r.type == "warmup_finished"]
    assert warmup.kind == "WARMUP"
    assert not warmup.awarded
    assert len(warmup.recall_test) == count


@then("o histórico não tem aquecimentos")
def then_no_warmups(world: World) -> None:
    records = world.run(world.history.list_for(str(world.learner_id), 100))
    assert not [r for r in records if r.type == "warmup_finished"]


@then("não há aquecimento em andamento")
def then_no_active(world: World) -> None:
    assert world.plan().current_warmup(world.clock.now()) is None


@then(parsers.parse('o próximo passo é revisar "{title}"'))
def then_next_review(warming: Warming, title: str) -> None:
    assert warming.next is not None
    assert (warming.next.title, warming.next.kind) == (title, SessionKind.REVIEW)


@then(parsers.parse('o próximo passo é estudar "{title}"'))
def then_next_study(warming: Warming, title: str) -> None:
    assert warming.next is not None
    assert (warming.next.title, warming.next.kind) == (title, SessionKind.STUDY)


@given(parsers.parse('que estudei "{title}" hoje'))
def given_studied_today(world: World, title: str) -> None:
    content = world.content(title)
    world.run(world.uc.start_session(world.learner_id, content.id.value))
    world.clock.advance(minutes=25)
    world.run(world.uc.finish_session(world.learner_id, GOOD_NOTES, None, []))


@then("não há próximo passo sugerido")
def then_no_next(warming: Warming) -> None:
    assert warming.next is None
