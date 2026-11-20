"""Suíte de CONTRATO do caderno: a mesma bateria roda no fake e no Mongo (ADR-0003)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker

from developer_myself.learning.adapters.memory.notebook_repository import (
    InMemoryNotebookRepository,
)
from developer_myself.learning.adapters.mongo.notebook_repository import MongoNotebookRepository
from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.notebook import Notebook
from developer_myself.learning.domain.repository import NotebookRepository
from developer_myself.learning.domain.value_objects import ContentId, LearnerId
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client

NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)


@pytest.fixture(
    params=["memory", pytest.param("mongo", marks=[pytest.mark.integration, requires_docker])]
)
async def repository(request: pytest.FixtureRequest) -> AsyncIterator[NotebookRepository]:
    if request.param == "memory":
        yield InMemoryNotebookRepository()
        return
    url: str = request.getfixturevalue("mongo_url")
    client = make_client(url)
    name = f"contract_nb_{uuid.uuid4().hex[:12]}"
    db: AsyncDatabase[Doc] = client[name]
    await ensure_schema(db)
    yield MongoNotebookRepository(db.notebooks)
    await client.drop_database(name)
    await client.close()


def written(
    text: str = "conceito", at: datetime = NOW, learner: LearnerId | None = None
) -> Notebook:
    nb = Notebook.empty(learner or LearnerId.new(), ContentId.new())
    nb.edit(text, 0, at)
    return nb


async def test_missing_notebook_is_none(repository: NotebookRepository) -> None:
    assert await repository.get(LearnerId.new(), ContentId.new()) is None


async def test_save_then_get_round_trips(repository: NotebookRepository) -> None:
    nb = written("Funções pequenas fazem uma coisa só")
    await repository.save(nb)
    assert nb.version == 1
    loaded = await repository.get(nb.learner_id, nb.content_id)
    assert loaded == nb


async def test_second_save_increments_version(repository: NotebookRepository) -> None:
    nb = written()
    await repository.save(nb)
    nb.edit("mais", 1, NOW + timedelta(minutes=1))
    await repository.save(nb)
    loaded = await repository.get(nb.learner_id, nb.content_id)
    assert loaded is not None
    assert loaded.version == 2
    assert loaded.text == "mais"


async def test_stale_save_raises_concurrency_error(repository: NotebookRepository) -> None:
    nb = written()
    await repository.save(nb)
    tab1 = await repository.get(nb.learner_id, nb.content_id)
    tab2 = await repository.get(nb.learner_id, nb.content_id)
    assert tab1 is not None
    assert tab2 is not None
    tab1.edit("aba 1", 1, NOW)
    tab2.edit("aba 2", 1, NOW)
    await repository.save(tab1)
    with pytest.raises(ConcurrencyError):
        await repository.save(tab2)


async def test_two_first_saves_conflict(repository: NotebookRepository) -> None:
    learner, content = LearnerId.new(), ContentId.new()
    a, b = Notebook.empty(learner, content), Notebook.empty(learner, content)
    a.edit("a", 0, NOW)
    b.edit("b", 0, NOW)
    await repository.save(a)
    with pytest.raises(ConcurrencyError):
        await repository.save(b)


async def test_other_learner_cannot_read(repository: NotebookRepository) -> None:
    nb = written()
    await repository.save(nb)
    assert await repository.get(LearnerId.new(), nb.content_id) is None


async def test_list_for_returns_most_recent_first_and_only_mine(
    repository: NotebookRepository,
) -> None:
    me = LearnerId.new()
    old = written("velho", NOW, me)
    new = written("novo", NOW + timedelta(hours=1), me)
    other = written("de outro")
    for nb in (old, new, other):
        await repository.save(nb)
    listed = await repository.list_for(me)
    assert [n.text for n in listed] == ["novo", "velho"]


async def test_delete_and_delete_all(repository: NotebookRepository) -> None:
    me = LearnerId.new()
    a, b = written("a", learner=me), written("b", learner=me)
    other = written("de outro")
    for nb in (a, b, other):
        await repository.save(nb)
    await repository.delete(me, a.content_id)
    await repository.delete(me, a.content_id)  # idempotente
    assert await repository.get(me, a.content_id) is None
    await repository.delete_all(me)
    assert await repository.list_for(me) == []
    assert await repository.get(other.learner_id, other.content_id) is not None
