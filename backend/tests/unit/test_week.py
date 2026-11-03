from datetime import date

import pytest

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.week import (
    MAX_COMPETENCIES_PER_DAY,
    BlockKind,
    Track,
    WeekDay,
    _Cursor,
    _review_blocks,
    build_week,
)
from developer_myself.learning.domain.errors import InvalidValueError
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    LearnerId,
    StudyPreferences,
    Timezone,
)

MONDAY = date(2026, 11, 2)


def track(title: str, competency: str, day: int = 1) -> Track:
    return Track(title, title, competency, competency, day, schedule_for(title))


def week(
    study: list[Track], reviews: list[Track], minutes: int = 210, rest: frozenset[int] = frozenset()
) -> list[WeekDay]:
    return build_week(study, reviews, minutes_per_day=minutes, rest_days=rest, start=MONDAY)


def test_without_reviews_all_time_goes_to_study() -> None:
    days = week([track("A", "a"), track("B", "b"), track("C", "c")], [])
    assert all(b.kind is not BlockKind.REVIEW for d in days for b in d.blocks)
    assert days[0].minutes == 210
    assert days[0].name == "segunda"


def test_without_study_reviews_use_up_to_4_competencies() -> None:
    reviews = [track(t, t.lower()) for t in "ABCDE"]
    day = week([], reviews, minutes=150)[0]  # 5 pomodoros em 4 revisões: 2 + 1 + 1 + 1
    assert len(day.competencies) == MAX_COMPETENCIES_PER_DAY
    assert day.minutes == 150
    assert [b.pomodoros for b in day.blocks] == [2, 1, 1, 1]


def test_one_hour_day_is_only_review() -> None:
    day = week([track("A", "a")], [track("R", "r")], minutes=60)[0]
    assert [b.kind for b in day.blocks] == [BlockKind.REVIEW]


def test_review_of_same_competency_does_not_count_twice() -> None:
    day = week([track("A", "go"), track("B", "b"), track("C", "c")], [track("R", "go")])[0]
    assert day.competencies == ["go", "b", "c"]


def test_review_that_would_be_the_5th_competency_waits() -> None:
    study = [track("A", "a"), track("B", "b"), track("C", "c")]
    day = week(study, [track("R1", "r1"), track("R2", "r2")])[0]
    assert len(day.competencies) == 4
    assert [b.track.title for b in day.blocks if b.kind is BlockKind.REVIEW] == ["R1"]


def test_no_review_fits_returns_nothing() -> None:
    taken = ["a", "b", "c", "d"]
    assert _review_blocks([track("R", "r")], 0, 2, taken, _Cursor(), max_picks=2) == []


def test_challenge_block_lists_every_challenge_it_covers() -> None:
    day = week([track("Linux", "fundamentos", day=8)], [], minutes=90)[0]
    assert day.blocks[0].kind is BlockKind.CHALLENGE
    assert day.blocks[0].focus.count("Desafio de Intermediário") == 3


class TestPreferences:
    def test_defaults(self) -> None:
        prefs = StudyPreferences()
        assert (prefs.minutes_per_day, prefs.rest_days) == (210, frozenset())

    @pytest.mark.parametrize(
        ("minutes", "rest"),
        [(59, frozenset()), (481, frozenset()), (200, frozenset({7})), (200, frozenset(range(7)))],
    )
    def test_invalid(self, minutes: int, rest: frozenset[int]) -> None:
        with pytest.raises(InvalidValueError):
            StudyPreferences(minutes, rest)

    def test_change_is_recorded_once(self) -> None:
        plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
        now = __import__("datetime").datetime(2026, 11, 2, tzinfo=__import__("datetime").UTC)
        plan.change_preferences(StudyPreferences(240, frozenset({6})), now)
        plan.change_preferences(StudyPreferences(240, frozenset({6})), now)
        assert len(plan.pull_events()) == 1
