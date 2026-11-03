from datetime import UTC, date, datetime, timedelta

import pytest

from developer_myself.learning.domain.errors import InvalidValueError
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    Duration,
    Evidence,
    LearnerId,
    MasteryLevel,
    Notes,
    Points,
    Timezone,
    Title,
)


class TestIds:
    def test_ids_are_uuid7_and_time_ordered(self) -> None:
        first, second = ContentId.new(), ContentId.new()
        assert first.value.version == 7
        assert first.value < second.value

    def test_str(self) -> None:
        for cls in (LearnerId, ContentId, ChallengeId):
            new = cls.new()
            assert str(new) == str(new.value)


class TestTitle:
    def test_strips(self) -> None:
        assert Title("  Clean Code ").value == "Clean Code"
        assert str(Title("DDD")) == "DDD"

    @pytest.mark.parametrize("value", ["", "   ", "x" * 201])
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            Title(value)


class TestPoints:
    def test_add_returns_new_value(self) -> None:
        points = Points(1)
        assert points.add() == Points(2)
        assert points == Points(1)
        assert int(points.add(3)) == 4

    def test_rejects_negative(self) -> None:
        with pytest.raises(InvalidValueError):
            Points(-1)


class TestDuration:
    def test_between(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        assert Duration.between(start, start + timedelta(minutes=25)) == Duration.minutes(25)
        assert Duration.hours(1).total_seconds == 3600

    def test_ordering(self) -> None:
        assert Duration.minutes(24) < Duration.minutes(25) <= Duration.hours(4)

    def test_rejects_negative(self) -> None:
        with pytest.raises(InvalidValueError):
            Duration(timedelta(seconds=-1))


class TestNotes:
    def test_substantive_requires_three_fields_and_50_chars(self) -> None:
        notes = Notes("a" * 20, "b" * 20, "c" * 10)
        assert notes.char_count == 50
        assert notes.is_substantive

    def test_spaces_do_not_count(self) -> None:
        notes = Notes("a " * 20, "b " * 20, "c " * 9)
        assert notes.char_count == 49
        assert not notes.is_substantive

    def test_missing_field_is_not_substantive(self) -> None:
        assert not Notes("a" * 40, "b" * 40, "").is_substantive

    def test_rejects_huge_field(self) -> None:
        with pytest.raises(InvalidValueError):
            Notes("a" * 10_001)


class TestTimezone:
    def test_local_date(self) -> None:
        tz = Timezone("America/Sao_Paulo")
        assert tz.local_date(datetime(2026, 11, 2, 1, 0, tzinfo=UTC)) == date(2026, 11, 1)
        assert str(tz) == "America/Sao_Paulo"

    @pytest.mark.parametrize("name", ["Mars/Olympus", "../etc"])
    def test_rejects_unknown(self, name: str) -> None:
        with pytest.raises(InvalidValueError):
            Timezone(name)


class TestEvidence:
    def test_strips(self) -> None:
        assert str(Evidence("  link ")) == "link"

    @pytest.mark.parametrize("value", ["", "  ", "x" * 10_001])
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidValueError):
            Evidence(value)


class TestMasteryLevel:
    def test_rank_order(self) -> None:
        assert MasteryLevel.ADVANCED.at_least(MasteryLevel.INTERMEDIATE)
        assert not MasteryLevel.BEGINNER.at_least(MasteryLevel.INTERMEDIATE)
