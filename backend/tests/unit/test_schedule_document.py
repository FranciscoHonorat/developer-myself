from datetime import date

from developer_myself.curriculum.adapters.markdown import TrailItem, render
from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.week import Track, build_week

TODAY = date(2026, 11, 2)
ITEMS = [
    TrailItem("Redes", "CONSOLIDATED", 12),
    TrailItem("Linux", "IN_PROGRESS", 3),
    TrailItem("Git e colaboração", "LOCKED", 0),
    TrailItem("Docker", "LOCKED", 0),
]
STARTS = {"Git e colaboração": date(2026, 11, 9), "Docker": date(2026, 11, 19)}


def test_document_has_overview_and_one_30_day_table_per_content() -> None:
    doc = render(ITEMS, TODAY, starts=STARTS, finish=date(2027, 10, 1))
    assert doc.startswith("# Cronograma de estudos diários")
    row = "| 3 | [Git e colaboração](#c3) | 1. Fundamentos comuns | Profundo | na fila | - "
    assert f"{row}| 09/11/2026 |" in doc
    assert doc.count("| Dia | Tipo | Foco | Aquecimento de memória |") == 4
    assert "| 4 ◀ hoje |" in doc  # Linux com 3 pontos está no dia 4
    assert "| ✅ 3 |" in doc
    assert (
        "começa por volta de **11/2026** e tudo chega ao Avançado por volta de **10/2027**" in doc
    )
    assert "Até 3 conteúdos em andamento" in doc


def test_week_section() -> None:
    track = Track("l", "Linux", "fundamentos", "Fundamentos", 4, schedule_for("Linux"))
    week = build_week([track], [], minutes_per_day=180, rest_days=frozenset({6}), start=TODAY)
    doc = render(ITEMS, TODAY, starts=STARTS, week=week)
    assert "## Semana-modelo (próximos 7 dias)" in doc
    assert "| segunda 02/11 | 3h00 | Fundamentos |" in doc
    assert "| domingo 08/11 | folga | - | 🌿 |" in doc


def test_pipes_in_titles_do_not_break_tables() -> None:
    doc = render([TrailItem("A | B", "LOCKED", 0)], TODAY)
    assert "A \\| B" in doc
