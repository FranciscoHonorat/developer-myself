"""Steps da ficha de competências, sobre a trilha real em memória."""

import pytest
from pytest_bdd import parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.competency_sheet import competency_sheet
from developer_myself.curriculum.domain.progression import CompetencyScore, Sheet

scenarios("competencias.feature")


@when("eu consulto minha ficha de competências", target_fixture="sheet")
def when_sheet(world: World) -> Sheet:
    return competency_sheet(world.plan(), world.clock.now())


def score(sheet: Sheet, name: str) -> CompetencyScore:
    return next(s for s in sheet.competencies if s.competency.name == name)


@then(parsers.parse('a competência "{name}" está acima de {value:d}'))
def then_above(sheet: Sheet, name: str, value: int) -> None:
    assert score(sheet, name).score > value


@then(parsers.parse('a competência "{name}" está abaixo de {value:d}'))
def then_below(sheet: Sheet, name: str, value: int) -> None:
    assert score(sheet, name).score < value


@then(parsers.parse('a competência "{name}" vale {value:d}'))
def then_equals(sheet: Sheet, name: str, value: int) -> None:
    assert score(sheet, name).score == value


@then(parsers.parse('sou "{title}"'))
def then_title(sheet: Sheet, title: str) -> None:
    assert title in [s.title for s in sheet.competencies]


@then(parsers.parse('a competência "{name}" não perdeu nada para a ferrugem'))
def then_no_rust(sheet: Sheet, name: str) -> None:
    s = score(sheet, name)
    assert s.rust_lost == 0
    assert s.score == s.peak


@then(parsers.parse('a competência "{name}" perdeu {pct:d}% para a ferrugem'))
def then_rust(sheet: Sheet, name: str, pct: int) -> None:
    s = score(sheet, name)
    assert s.score == pytest.approx(s.peak * (1 - pct / 100), abs=0.15)
    assert s.status == "enferrujando"


@then(parsers.parse('a competência "{name}" enferruja em {days:d} dias'))
def then_rust_soon(sheet: Sheet, name: str, days: int) -> None:
    s = score(sheet, name)
    assert s.rust_in_days == days
    assert s.status == "enferruja em breve"
