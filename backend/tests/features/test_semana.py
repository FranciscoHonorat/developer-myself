"""Steps da semana planejada (trilha real em memória + modelo de recomendação)."""

from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.conftest import World

from developer_myself.curriculum.domain.week import BlockKind, WeekDay
from developer_myself.insights.adapters.neural.recommender import load_best_recommender
from developer_myself.planning.application.weekly_plan import weekly_plan

scenarios("semana.feature")
WEEKDAYS = {
    "segunda": 0,
    "terça": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sábado": 5,
    "domingo": 6,
}


@given(parsers.parse("que eu estudo {minutes:d} minutos por dia"))
def given_minutes(world: World, minutes: int) -> None:
    rest = sorted(world.plan().preferences.rest_days)
    world.run(world.uc.change_preferences(world.learner_id, minutes, rest))


@given(parsers.parse("que {day} é meu dia de folga"))
def given_rest_day(world: World, day: str) -> None:
    prefs = world.plan().preferences
    rest = sorted(prefs.rest_days | {WEEKDAYS[day]})
    world.run(world.uc.change_preferences(world.learner_id, prefs.minutes_per_day, rest))


@given(parsers.parse('que "{title}" tem {points:d} pontos'))
def given_points(world: World, title: str, points: int) -> None:
    world.earn_points(title, points - world.content(title).points.value)


@when("eu consulto a semana", target_fixture="week")
def when_week(world: World) -> list[WeekDay]:
    return weekly_plan(world.plan(), load_best_recommender(), world.clock.now())


def study_days(week: list[WeekDay]) -> list[WeekDay]:
    return [d for d in week if not d.is_rest]


@then(parsers.parse("cada dia de estudo soma {minutes:d} minutos"))
def then_minutes(week: list[WeekDay], minutes: int) -> None:
    assert [d.minutes for d in study_days(week)] == [minutes] * len(study_days(week))


@then(parsers.parse("cada dia de estudo tem entre {low:d} e {high:d} competências diferentes"))
def then_competencies(week: list[WeekDay], low: int, high: int) -> None:
    assert all(low <= len(d.competencies) <= high for d in study_days(week)), [
        d.competencies for d in week
    ]


@then("cada dia começa com revisão")
def then_review_first(week: list[WeekDay]) -> None:
    # Os consolidados mudam ao longo da semana (quem chega a Intermediário entra no rodízio),
    # mas todo dia de estudo abre com um bloco de revisão.
    assert all(d.blocks[0].kind is not BlockKind.STUDY for d in study_days(week))


@then("os 3 conteúdos em andamento aparecem todos os dias até chegarem a Intermediário")
def then_all_tracks(week: list[WeekDay]) -> None:
    days = study_days(week)
    for title in ("Learning Go", "SAST/DAST/SCA", "Designing Web APIs"):
        studied = [
            any(b.track.title == title and b.kind is not BlockKind.REVIEW for b in d.blocks)
            for d in days
        ]
        streak = studied.index(False) if False in studied else len(studied)
        assert streak >= 3, (title, studied)  # sem buracos enquanto está em andamento
        assert not any(studied[streak:]), (title, studied)


@then(parsers.parse('quem chega a Intermediário dá a vaga para "{title}" na mesma semana'))
def then_slot_reused(week: list[WeekDay], title: str) -> None:
    days = study_days(week)
    assert all(b.track.title != title for b in days[0].blocks)  # hoje ainda está na fila
    assert any(
        b.track.title == title and b.kind is not BlockKind.REVIEW
        for d in days[1:]
        for b in d.blocks
    ), "a vaga aberta não foi para o próximo da fila"


@then(parsers.parse("{day} não tem estudo"))
def then_rest(week: list[WeekDay], day: str) -> None:
    rest = next(d for d in week if d.weekday == WEEKDAYS[day])
    assert rest.is_rest
    assert rest.minutes == 0


def blocks_of(week: list[WeekDay], title: str) -> list[object]:
    return [b for d in week for b in d.blocks if b.track.title == title]


@then(parsers.parse('o primeiro bloco de "{title}" cobre os dias a partir do dia {day:d}'))
def then_first_block(week: list[WeekDay], title: str, day: int) -> None:
    assert blocks_of(week, title)[0].first_day == day  # type: ignore[attr-defined]


@then(parsers.parse('o cronograma de "{title}" avança ao longo da semana'))
def then_advances(week: list[WeekDay], title: str) -> None:
    firsts = [b.first_day for b in blocks_of(week, title)]  # type: ignore[attr-defined]
    assert firsts == sorted(firsts)
    assert firsts[-1] > firsts[0]


@then(parsers.parse('há um bloco de desafio de "{title}" na semana'))
def then_challenge(week: list[WeekDay], title: str) -> None:
    kinds = [b.kind for b in blocks_of(week, title)]  # type: ignore[attr-defined]
    assert BlockKind.CHALLENGE in kinds


@then(parsers.parse('"{title}" é revisado em pelo menos {n:d} dias'))
def then_reviewed_days(week: list[WeekDay], title: str, n: int) -> None:
    days = [d for d in week if any(b.track.title == title for b in d.blocks)]
    assert len(days) >= n, [[b.track.title for b in d.blocks] for d in week]


@then(parsers.parse('"{title}" tem {n:d} pomodoros em cada dia de estudo'))
def then_daily_pomodoros(week: list[WeekDay], title: str, n: int) -> None:
    per_day = [
        sum(b.pomodoros for b in d.blocks if b.track.title == title) for d in study_days(week)
    ]
    assert per_day == [n] * len(per_day), per_day
