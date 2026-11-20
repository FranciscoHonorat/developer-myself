"""Caderno da matéria: bloco livre, concorrência otimista e limite de tamanho."""

from datetime import UTC, datetime

import pytest

from developer_myself.learning.domain.errors import InvalidValueError, NotebookConflictError
from developer_myself.learning.domain.notebook import NOTEBOOK_MAX_CHARS, Notebook
from developer_myself.learning.domain.value_objects import ContentId, LearnerId
from developer_myself.shared.adapters.mongo_setup import NOTEBOOK_SCHEMA

NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)


def notebook() -> Notebook:
    return Notebook.empty(LearnerId.new(), ContentId.new())


def test_empty_notebook_starts_at_version_zero() -> None:
    nb = notebook()
    assert nb.text == ""
    assert nb.version == 0
    assert nb.updated_at is None
    assert nb.chars == 0


def test_edit_replaces_text_and_stamps_time() -> None:
    nb = notebook()
    nb.edit("conceito", 0, NOW)
    assert nb.text == "conceito"
    assert nb.updated_at == NOW
    assert nb.version == 0  # quem incrementa é o repositório ao salvar
    assert nb.chars == 8


def test_edit_with_stale_version_is_refused() -> None:
    nb = notebook()
    nb.edit("original", 0, NOW)
    nb.version = 2
    with pytest.raises(NotebookConflictError):
        nb.edit("x", 1, NOW)
    assert nb.text == "original"


def test_edit_accepts_exactly_the_limit() -> None:
    nb = notebook()
    nb.edit("a" * NOTEBOOK_MAX_CHARS, 0, NOW)
    assert nb.chars == 100_000


def test_edit_over_the_limit_is_refused() -> None:
    nb = notebook()
    with pytest.raises(InvalidValueError):
        nb.edit("a" * 100_001, 0, NOW)
    assert nb.text == ""


def test_edit_to_empty_is_allowed() -> None:
    nb = notebook()
    nb.edit("x", 0, NOW)
    nb.edit("", 0, NOW)
    assert nb.text == ""


def test_mongo_validator_uses_the_domain_limit() -> None:
    assert NOTEBOOK_SCHEMA["properties"]["text"]["maxLength"] == NOTEBOOK_MAX_CHARS
