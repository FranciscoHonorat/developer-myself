from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.curriculum.domain.catalog import CATALOG
from developer_myself.curriculum.domain.competencies import (
    BY_KEY,
    SKILLS_BY_TITLE,
    Area,
    Tier,
    skills_for,
)
from developer_myself.curriculum.domain.progression import (
    ContentSnapshot,
    build_sheet,
    competency,
    level_for,
)
from developer_myself.curriculum.domain.schedule import Depth

NOW = datetime(2026, 11, 2, tzinfo=UTC)


def snap(
    title: str = "x",
    *,
    points: int = 0,
    inter: int = 0,
    adv: int = 0,
    idle: float | None = None,
    depth: Depth = Depth.PROFUNDO,
    skills: tuple[tuple[str, float], ...] = (("go", 1.0),),
) -> ContentSnapshot:
    last = NOW - timedelta(days=idle) if idle is not None else None
    return ContentSnapshot(title, points, inter, adv, last, depth, skills)


class TestTaxonomy:
    @pytest.mark.parametrize("entry", CATALOG, ids=lambda e: e.title[:40])
    def test_every_catalog_entry_has_explicit_weights(self, entry: object) -> None:
        weights = SKILLS_BY_TITLE[entry.title]  # type: ignore[attr-defined]
        assert sum(w for _, w in weights) == pytest.approx(1.0)
        assert all(key in BY_KEY for key, _ in weights)

    def test_unknown_content_counts_as_others(self) -> None:
        assert skills_for("Trilha de 30 dias: Inteligência e Investigação") == (("outros", 1.0),)
        assert skills_for("• TypeScript") == (("frontend", 1.0),)

    def test_tiers(self) -> None:
        assert [Tier.of(s) for s in (0, 24.9, 25, 50, 74.9, 75, 100)] == [
            Tier.APRENDIZ, Tier.APRENDIZ, Tier.PRATICANTE, Tier.PROFICIENTE,
            Tier.PROFICIENTE, Tier.ESPECIALISTA, Tier.ESPECIALISTA,
        ]  # fmt: skip

    def test_areas_follow_the_map(self) -> None:
        assert len(Area) == 8  # 6 do mapa + Inteligência e DFIR (perfil em T)
        assert competency("devsecops").area is Area.DEVSECOPS


class TestProgressAndRust:
    def test_progress_weights(self) -> None:
        assert snap(points=30, inter=3, adv=3).progress == pytest.approx(1.0)
        assert snap(points=10, inter=3).progress == pytest.approx(0.7 / 3 + 0.15)
        assert snap(points=99, inter=9, adv=9).progress == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("idle", "fresh"), [(None, 1.0), (0, 1.0), (21, 1.0), (31, 0.9), (71, 0.5), (500, 0.5)]
    )
    def test_freshness_curve(self, idle: float | None, fresh: float) -> None:
        assert snap(points=1, idle=idle).freshness(NOW) == pytest.approx(fresh)

    def test_rust_countdown(self) -> None:
        assert snap(points=1, idle=17).rust_in_days(NOW) == 4
        assert snap(points=1, idle=40).rust_in_days(NOW) == 0
        assert snap().rust_in_days(NOW) is None


class TestSheet:
    def test_depth_weights_the_average(self) -> None:
        deep = snap("Go a fundo", points=30, inter=3, adv=3, depth=Depth.PROFUNDO)
        light = snap("Go noção", depth=Depth.NOCAO)
        go = build_sheet([deep, light], NOW).competencies[0]
        assert go.score == pytest.approx(100 * 3 / 4)
        assert go.title == "Especialista em Go"

    def test_multi_skill_content_and_effort_by_area(self) -> None:
        gin = snap("Gin", points=10, idle=1, skills=(("backend", 0.5), ("go", 0.5)))
        sheet = build_sheet([gin], NOW)
        assert {s.competency.key for s in sheet.competencies} == {"go", "backend"}
        by_area = {a.area: a.points for a in sheet.effort}
        assert by_area[Area.FUNDAMENTOS] == 5
        assert by_area[Area.FULLSTACK] == 5
        assert sheet.total_points == 10

    def test_status(self) -> None:
        def status(idle: float | None, points: int = 3) -> str:
            return build_sheet([snap(points=points, idle=idle)], NOW).competencies[0].status

        assert status(None, points=0) == "sem progresso"
        assert status(2) == "em dia"
        assert status(16) == "enferruja em breve"
        assert status(30) == "enferrujando"

    def test_xp_and_level(self) -> None:
        sheet = build_sheet([snap(points=10, inter=3, idle=1)], NOW)
        assert sheet.xp == 10 * 10 + 3 * 25
        assert sheet.level == level_for(175) == 2
        assert sheet.next_level_xp == 200
        assert [level_for(x) for x in (0, 49, 50, 199, 200, 450)] == [1, 1, 2, 2, 3, 4]

    def test_empty_trail(self) -> None:
        sheet = build_sheet([], NOW)
        assert sheet.competencies == ()
        assert sheet.xp == 0
        assert sheet.level == 1
