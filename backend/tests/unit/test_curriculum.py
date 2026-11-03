"""Cronograma diário: casa com as regras de pontos e níveis do `learning`."""

import pytest

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.catalog import CATALOG, find_entry, map_entries
from developer_myself.curriculum.domain.schedule import (
    INTERMEDIATE_DAY,
    TOTAL_DAYS,
    CatalogEntry,
    DayKind,
    Depth,
    Phase,
    build_schedule,
    generic_entry,
    normalize,
    today_for,
)

ENTRY = CatalogEntry("Teste", "x", Depth.PROFUNDO, ("A", "B", "C", "D"), ("Lab 1",))


def test_normalize_ignores_case_accents_and_bullets() -> None:
    assert normalize("• TypeScript ") == normalize("typescript")
    assert normalize("Computação  e Sistemas") == "computacao e sistemas"


def test_today_is_points_plus_one_capped() -> None:
    assert today_for(0) == 1
    assert today_for(9) == INTERMEDIATE_DAY
    assert today_for(99) == TOTAL_DAYS


class TestBuild:
    schedule = build_schedule(ENTRY)

    def test_has_30_numbered_days(self) -> None:
        assert [d.day for d in self.schedule.days] == list(range(1, 31))

    def test_challenges_match_the_level_rules(self) -> None:
        """3 desafios de Intermediário até o dia 10 e 3 de Avançado até o dia 30."""
        by_level = {
            lvl: [d.day for d in self.schedule.days if d.target_level == lvl]
            for lvl in ("INTERMEDIATE", "ADVANCED")
        }
        assert by_level == {"INTERMEDIATE": [8, 9, 10], "ADVANCED": [26, 27, 28]}
        assert all(d.kind is DayKind.CHALLENGE for d in self.schedule.days if d.target_level)

    def test_phases(self) -> None:
        assert self.schedule.day(1).phase is Phase.FUNDAMENTOS
        assert self.schedule.day(10).phase is Phase.FUNDAMENTOS
        assert self.schedule.day(11).phase is Phase.APROFUNDAMENTO
        assert self.schedule.day(30).phase is Phase.DOMINIO

    def test_every_topic_is_studied(self) -> None:
        studied = " ".join(d.focus for d in self.schedule.days if d.kind is DayKind.STUDY)
        assert all(topic in studied for topic in ENTRY.topics)

    def test_spaced_review_warmups_at_1_3_and_7_days(self) -> None:
        """Método do mapa: revise de memória em 1 dia, 3 dias e 1 semana."""
        # "A" é estudado pela 1ª vez no dia 1 → volta nos dias 2, 4 e 8.
        days_with_a = [
            d.day for d in self.schedule.days if any(w.startswith("A (") for w in d.warmup)
        ]
        assert days_with_a == [2, 4, 8]
        assert self.schedule.day(2).warmup == ("A (1 dia atrás)",)
        assert self.schedule.day(1).warmup == ()

    def test_practice_days_do_not_schedule_extra_reviews(self) -> None:
        warmups = [w for d in self.schedule.days for w in d.warmup]
        assert not any(
            w.startswith(("prática guiada", "Laboratório", "Trade-offs")) for w in warmups
        )

    def test_practice_uses_the_map_environments(self) -> None:
        assert self.schedule.day(18).focus == "Laboratório: Lab 1"

    def test_day_is_clamped(self) -> None:
        assert self.schedule.day(0).day == 1
        assert self.schedule.day(31).day == 30


def test_many_topics_are_grouped_into_the_study_days() -> None:
    entry = CatalogEntry("Grande", "x", Depth.FUNCIONAL, tuple(f"T{i}" for i in range(20)))
    schedule = build_schedule(entry)
    studied = " ".join(d.focus for d in schedule.days)
    assert all(f"T{i}" in studied for i in range(20))
    assert len(schedule.days) == TOTAL_DAYS


def test_single_topic_and_empty_topics_still_build() -> None:
    assert len(build_schedule(CatalogEntry("Um", "x", Depth.NOCAO, ("só",))).days) == 30
    assert len(build_schedule(CatalogEntry("Zero", "x", Depth.NOCAO, ())).days) == 30


@pytest.mark.parametrize("entry", CATALOG, ids=lambda e: e.title[:40])
def test_every_catalog_entry_builds(entry: CatalogEntry) -> None:
    schedule = build_schedule(entry)
    assert len(schedule.days) == TOTAL_DAYS
    assert all(len(e.title) <= 200 for e in CATALOG)


def test_catalog_has_no_ambiguous_keys() -> None:
    seen: dict[str, str] = {}
    for entry in CATALOG:
        for key in entry.keys:
            assert key not in seen, f"{key!r} em {seen.get(key)!r} e {entry.title!r}"
            seen[key] = entry.title


def test_titles_from_the_learners_trail_are_found() -> None:
    for title in ("• TypeScript", "Typescript", "CI/CD", "Kubernetes com Heml e Chart",
                  "• YAML, JSON e HCL", "Observability", "SAST/DAST/SCA"):  # fmt: skip
        assert find_entry(title) is not None, title
    assert find_entry("CI/CD") == find_entry("ESTEIRA CI/CD (Jenkins, Bamboo e Github Actions)")


def test_map_entries_exclude_own_contents() -> None:
    titles = {e.title for e in map_entries()}
    assert "Linux" in titles
    assert "Conversação em Inglês" not in titles


def test_unknown_content_gets_a_generic_schedule() -> None:
    schedule = schedule_for("Trilha de 30 dias: Inteligência e Investigação")
    assert schedule.entry == generic_entry("Trilha de 30 dias: Inteligência e Investigação")
    assert "módulo/capítulo 1" in schedule.day(1).focus
    assert schedule_for("Linux").entry.title == "Linux"
    assert Depth.NOCAO.goal.startswith("Saber que existe")
