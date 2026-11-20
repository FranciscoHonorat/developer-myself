"""Steps do histórico paginado, sobre `HistoryQueries` com o store em memória."""

from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.insights.application.history import HistoryPage, HistoryQueries

scenarios("historico.feature")


@dataclass
class Browsing:
    page_size: int = 0
    page: HistoryPage | None = None
    # event_id -> nº da sessão (1 = a primeira estudada)
    numbers: dict[str, int] = field(default_factory=dict)


@pytest.fixture
def browsing() -> Browsing:
    return Browsing()


def number_sessions(world: World, browsing: Browsing) -> None:
    records = world.run(world.history.list_for(str(world.learner_id), 1_000))
    for n, r in enumerate(sorted(records, key=lambda r: r.finished_at), start=1):
        browsing.numbers.setdefault(r.event_id, n)


@given(parsers.parse('que estudei "{title}" {times:d} vezes'))
def given_studied(world: World, title: str, times: int) -> None:
    for _ in range(times):
        world.session(title, 25)


@when(parsers.parse("eu abro o histórico com {size:d} sessões por página"))
def when_open(world: World, browsing: Browsing, size: int) -> None:
    number_sessions(world, browsing)
    browsing.page_size = size
    browsing.page = world.run(HistoryQueries(world.history).page(world.learner_id, size))


@when("eu abro a próxima página")
def when_next(world: World, browsing: Browsing) -> None:
    assert browsing.page is not None
    assert browsing.page.next is not None
    browsing.page = world.run(
        HistoryQueries(world.history).page(
            world.learner_id, browsing.page_size, after=browsing.page.next
        )
    )


@then(parsers.parse("vejo as sessões {expected}"))
def then_sessions(browsing: Browsing, expected: str) -> None:
    assert browsing.page is not None
    seen = [browsing.numbers[r.event_id] for r in browsing.page.items]
    assert seen == [int(n) for n in expected.split(", ")]


@then("não vejo nenhuma sessão")
def then_empty(browsing: Browsing) -> None:
    assert browsing.page is not None
    assert browsing.page.items == []


@then("existe uma próxima página")
def then_has_next(browsing: Browsing) -> None:
    assert browsing.page is not None
    assert browsing.page.next is not None


@then("não existe próxima página")
def then_no_next(browsing: Browsing) -> None:
    assert browsing.page is not None
    assert browsing.page.next is None
