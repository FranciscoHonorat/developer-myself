from datetime import date

import pytest

from developer_myself.learning.domain.policies import (
    DefaultMasteryPolicy,
    DefaultScoringPolicy,
    ScoringContext,
)
from developer_myself.learning.domain.value_objects import (
    Duration,
    MasteryLevel,
    Notes,
    Points,
    SessionKind,
    WithheldReason,
)

GOOD = Notes("a" * 20, "b" * 20, "c" * 20)
TODAY = date(2026, 11, 2)


def ctx(**overrides: object) -> ScoringContext:
    base: dict[str, object] = {
        "kind": SessionKind.STUDY,
        "duration": Duration.minutes(25),
        "notes": GOOD,
        "has_reviewable_content": False,
        "last_review_on": None,
        "today": TODAY,
    }
    base.update(overrides)
    return ScoringContext(**base)  # type: ignore[arg-type]


class TestScoringPolicy:
    policy = DefaultScoringPolicy()

    def test_awards_qualified_session(self) -> None:
        assert self.policy.evaluate(ctx()).awarded

    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            ({"duration": Duration.minutes(24)}, WithheldReason.TOO_SHORT),
            ({"duration": Duration.minutes(241)}, WithheldReason.EXPIRED),
            ({"notes": Notes()}, WithheldReason.NO_NOTES),
            ({"has_reviewable_content": True}, WithheldReason.NO_REVIEW),
        ],
    )
    def test_withholds(self, overrides: dict[str, object], reason: WithheldReason) -> None:
        result = self.policy.evaluate(ctx(**overrides))
        assert not result.awarded
        assert result.reason is reason

    def test_four_hours_exactly_still_counts(self) -> None:
        assert self.policy.evaluate(ctx(duration=Duration.hours(4))).awarded

    def test_review_today_unlocks_study(self) -> None:
        assert self.policy.evaluate(ctx(has_reviewable_content=True, last_review_on=TODAY)).awarded

    def test_review_session_never_needs_previous_review(self) -> None:
        result = self.policy.evaluate(ctx(kind=SessionKind.REVIEW, has_reviewable_content=True))
        assert result.awarded


INTER, ADV = MasteryLevel.INTERMEDIATE, MasteryLevel.ADVANCED


class TestMasteryPolicy:
    policy = DefaultMasteryPolicy()

    @pytest.mark.parametrize(
        ("points", "solved", "expected"),
        [
            (0, [], MasteryLevel.BEGINNER),
            (15, [INTER], MasteryLevel.BEGINNER),
            (9, [INTER, INTER, INTER], MasteryLevel.BEGINNER),
            (10, [INTER, INTER, INTER], MasteryLevel.INTERMEDIATE),
            (30, [INTER, INTER, INTER, ADV, ADV], MasteryLevel.INTERMEDIATE),
            (29, [INTER, INTER, INTER, ADV, ADV, ADV], MasteryLevel.INTERMEDIATE),
            (30, [INTER, INTER, INTER, ADV, ADV, ADV], MasteryLevel.ADVANCED),
            (30, [ADV, ADV, ADV], MasteryLevel.BEGINNER),
        ],
    )
    def test_level(self, points: int, solved: list[MasteryLevel], expected: MasteryLevel) -> None:
        assert self.policy.level_for(Points(points), solved) is expected

    def test_requirements_exposed(self) -> None:
        assert self.policy.requirements()[MasteryLevel.INTERMEDIATE] == (10, 3)
