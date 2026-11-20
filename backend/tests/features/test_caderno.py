"""Steps do caderno da matéria, sobre os casos de uso com repositórios em memória."""

import uuid

from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.learning.domain.errors import (
    ContentNotFoundError,
    InvalidValueError,
    NotebookConflictError,
)
from developer_myself.learning.domain.value_objects import ContentId, LearnerId

scenarios("caderno.feature")


def _text(raw: str) -> str:
    return raw.replace("\\n", "\n")


def write(world: World, title: str, text: str) -> None:
    content_id = world.content(title).id.value
    current = world.run(world.uc.notebooks.get(world.learner_id, content_id))
    world.run(world.uc.notebooks.save(world.learner_id, content_id, text, current.version))


@given(parsers.parse('que escrevi no caderno de "{title}"'))
def given_written(world: World, title: str) -> None:
    write(world, title, "primeira versão")


@when(parsers.parse('eu escrevo no caderno de "{title}": "{text}"'))
def when_write(world: World, title: str, text: str) -> None:
    write(world, title, _text(text))


@when(parsers.parse('eu apago o caderno de "{title}"'))
def when_clear(world: World, title: str) -> None:
    write(world, title, "")


@when(parsers.parse('eu escrevo no caderno de "{title}" a partir de uma versão antiga'))
def when_write_stale(world: World, title: str) -> None:
    content_id = world.content(title).id.value
    current = world.run(world.uc.notebooks.get(world.learner_id, content_id))
    world.attempt(
        world.uc.notebooks.save(world.learner_id, content_id, "outra aba", current.version - 1)
    )


@when("eu tento escrever no caderno de uma matéria que não existe")
def when_write_missing(world: World) -> None:
    world.attempt(world.uc.notebooks.save(world.learner_id, uuid.uuid7(), "texto", 0))


@when(parsers.parse('eu tento escrever {amount:d} caracteres no caderno de "{title}"'))
def when_write_too_much(world: World, amount: int, title: str) -> None:
    content_id = world.content(title).id.value
    world.attempt(world.uc.notebooks.save(world.learner_id, content_id, "a" * amount, 0))


@then(parsers.parse('o caderno de "{title}" diz "{text}"'))
def then_says(world: World, title: str, text: str) -> None:
    notebook = world.run(world.uc.notebooks.get(world.learner_id, world.content(title).id.value))
    assert notebook.text == _text(text)


@then(parsers.parse('o caderno de "{title}" está vazio'))
def then_empty(world: World, title: str) -> None:
    notebook = world.run(world.uc.notebooks.get(world.learner_id, world.content(title).id.value))
    assert notebook.text == ""
    assert notebook.version > 0  # foi salvo vazio, não é um caderno que nunca existiu


@then("o salvamento do caderno é recusado por conflito")
def then_conflict(world: World) -> None:
    assert isinstance(world.error, NotebookConflictError)


@then("o salvamento do caderno é recusado porque a matéria não existe")
def then_missing(world: World) -> None:
    assert isinstance(world.error, ContentNotFoundError)


@then("o salvamento do caderno é recusado por tamanho")
def then_too_long(world: World) -> None:
    assert isinstance(world.error, InvalidValueError)


@then(parsers.parse('não existe caderno para "{title}"'))
def then_no_notebook(world: World, title: str) -> None:
    removed = world.removed_ids[title]
    assert world.run(world.notebooks.get(LearnerId(world.learner_id), ContentId(removed))) is None
