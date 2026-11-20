"""Steps do teste de memória da revisão, sobre os casos de uso em memória."""

from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import GOOD_NOTES, World, last_finished

from developer_myself.learning.application.use_cases import NotesInput, StartSession
from developer_myself.learning.domain.errors import RecallTestRequiredError
from developer_myself.learning.domain.study_plan import ActiveSession

scenarios("teste_de_memoria.feature")


def _active(world: World) -> ActiveSession:
    session = world.plan().active_session
    assert session is not None
    return session


@given(parsers.parse('que anotei para revisar em "{title}": "{text}"'))
def given_to_review(world: World, title: str, text: str) -> None:
    notes = NotesInput(GOOD_NOTES.studied, GOOD_NOTES.understood, text)
    world.session(title, 25, notes)


@given(parsers.parse('que uma revisão de "{title}" foi aberta antes do teste existir'))
def given_review_without_test(world: World, title: str) -> None:
    legacy = StartSession(world.repository, world.clock)  # sem quem escolha perguntas
    world.run(legacy(world.learner_id, world.content(title).id.value))
    assert _active(world).questions == ()


@when(parsers.parse("eu finalizo a revisão {minutes:d} minutos depois sem responder o teste"))
def when_finish_without_test(world: World, minutes: int) -> None:
    world.clock.advance(minutes=minutes)
    world.attempt(world.uc.finish_session(world.learner_id, GOOD_NOTES, 3))


@when(parsers.parse("eu finalizo a revisão {minutes:d} minutos depois errando todas"))
def when_finish_missing_all(world: World, minutes: int) -> None:
    world.clock.advance(minutes=minutes)
    world.outcome = world.run(
        world.uc.finish_session(world.learner_id, GOOD_NOTES, 1, world.answers("MISSED"))
    )


@when(parsers.parse('eu estudo "{title}" por {minutes:d} minutos anotando para revisar "{text}"'))
def when_study_with_to_review(world: World, title: str, minutes: int, text: str) -> None:
    notes = NotesInput(GOOD_NOTES.studied, GOOD_NOTES.understood, text)
    world.session(title, minutes, notes)


@then(parsers.parse("a sessão tem {amount:d} perguntas de memória"))
def then_has_questions(world: World, amount: int) -> None:
    questions = _active(world).questions
    assert len(questions) == amount
    assert len({q.text for q in questions}) == amount


@then("a sessão não tem perguntas de memória")
def then_no_questions(world: World) -> None:
    assert _active(world).questions == ()


@then(parsers.parse('a 1ª pergunta é "{text}"'))
def then_first_question(world: World, text: str) -> None:
    assert _active(world).questions[0].text == text


@then("a finalização é recusada pedindo o teste")
def then_test_required(world: World) -> None:
    assert isinstance(world.error, RecallTestRequiredError)


@then(parsers.parse('o último "preciso revisar" de "{title}" é "{text}"'))
def then_last_to_review(world: World, title: str, text: str) -> None:
    assert world.content(title).last_to_review == text


@then("o histórico registra 3 perguntas com as minhas correções")
def then_history_has_test(world: World) -> None:
    assert len(last_finished(world).recall_test) == 3  # o evento carrega o teste…
    records = world.run(world.history.list_for(str(world.learner_id), 1))
    items = records[0].recall_test  # …e a projeção do histórico guarda
    assert len(items) == 3
    assert [i["grade"] for i in items] == ["MISSED"] * 3
    assert [i["position"] for i in items] == [0, 1, 2]
