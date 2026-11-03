"""Steps do cronograma: plano de hoje montado sobre a trilha real (casos de uso em memória)."""

from pytest_bdd import parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.curriculum.domain.schedule import DayKind
from developer_myself.daily_plan import DailyPlan, daily_plan
from developer_myself.insights.adapters.neural.recommender import load_best_recommender

scenarios("cronograma.feature")


@when("eu consulto o plano de hoje", target_fixture="today")
def when_today(world: World) -> DailyPlan:
    return daily_plan(world.plan(), load_best_recommender(), world.clock.now())


@then(parsers.parse('devo estudar "{title}" no dia {day:d} de 30'))
def then_study(today: DailyPlan, title: str, day: int) -> None:
    assert (title, day) in [(s.title, s.day) for s in today.studies]


@then(parsers.parse('devo revisar "{title}" no dia {day:d} de 30'))
def then_review(today: DailyPlan, title: str, day: int) -> None:
    assert [(r.title, r.day) for r in today.reviews] == [(title, day)]


@then(parsers.parse('o foco do dia fala de "{text}"'))
def then_focus(today: DailyPlan, text: str) -> None:
    assert any(text in s.plan.focus for s in today.studies)


@then(parsers.parse('o dia de "{title}" é um desafio de Intermediário'))
def then_challenge(today: DailyPlan, title: str) -> None:
    study = next(s for s in today.studies if s.title == title)
    assert study.plan.kind is DayKind.CHALLENGE
    assert study.plan.target_level == "INTERMEDIATE"
