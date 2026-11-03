"""Gera `Docs/Cronograma de estudos.md` a partir da trilha real (em andamento + fila).

As datas vêm da projeção simulada (`projection.py`): as regras reais do domínio, até 3 em
paralelo e o ritmo escolhido. Inclui a semana-modelo. `make schedule-doc` (stack no ar).
"""

import asyncio
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.schedule import (
    TOTAL_DAYS,
    DayKind,
    today_for,
)
from developer_myself.curriculum.domain.week import (
    POMODORO_MINUTES,
    STUDY_MINUTES,
    BlockKind,
    WeekDay,
)

BLOCK = {
    BlockKind.REVIEW: "🔁 Revisão",
    BlockKind.STUDY: "📖 Estudo",
    BlockKind.CHALLENGE: "🎯 Desafio",
}
KIND = {
    DayKind.STUDY: "📖 Estudo",
    DayKind.PRACTICE: "🛠 Prática",
    DayKind.CHALLENGE: "🎯 Desafio",
    DayKind.TEACH: "🗣 Ensinar",
    DayKind.REVIEW: "🔁 Revisão",
}
STATUS = {
    "IN_PROGRESS": "em andamento",
    "LOCKED": "na fila",
    "CONSOLIDATED": "consolidado",
    "FINISHED": "concluído",
}


@dataclass(frozen=True, slots=True)
class TrailItem:
    title: str
    status: str
    points: int


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _anchor(n: int) -> str:
    return f"c{n}"


def week_section(week: list[WeekDay]) -> list[str]:
    """A semana-modelo: dia por blocos (revisões primeiro), em pomodoros de 30 min."""
    out = [
        "## Semana-modelo (próximos 7 dias)",
        "",
        f"Pomodoros de {POMODORO_MINUTES} min ({STUDY_MINUTES} de estudo + "
        f"{POMODORO_MINUTES - STUDY_MINUTES} de pausa). Revisões primeiro: elas liberam a "
        "pontuação do estudo. A semana se refaz sozinha a cada sessão (tela **Semana**).",
        "",
        "| Dia | Tempo | Competências | Blocos |",
        "|---|---|---|---|",
    ]
    for d in week:
        if d.is_rest:
            out.append(f"| {d.name} {d.date:%d/%m} | folga | - | 🌿 |")
            continue
        blocks = "<br>".join(
            f"{BLOCK[b.kind]} {_cell(b.track.title)} · {b.pomodoros}x{STUDY_MINUTES} min "
            f"(dias {b.first_day} a {b.last_day})"
            for b in d.blocks
        )
        names = ", ".join(dict.fromkeys(b.track.competency_name for b in d.blocks))
        time = f"{d.minutes // 60}h{d.minutes % 60:02d}"
        out.append(f"| {d.name} {d.date:%d/%m} | {time} | {names} | {blocks} |")
    return out


def render(
    items: list[TrailItem],
    today: date,
    *,
    starts: Mapping[str, date | None] | None = None,
    week: list[WeekDay] | None = None,
    finish: date | None = None,
    max_in_progress: int = 3,
) -> str:
    starts = starts or {}
    out = [
        "# Cronograma de estudos diários",
        "",
        f"Gerado em {today:%d/%m/%Y} a partir da trilha (em andamento, depois a fila) e do "
        "*Mapa de conteúdos* + perfil em T (Inteligência e DFIR). A versão viva fica nas telas "
        "**Trilha → 📅 Hoje / 📅 Cronograma** e **Semana** do Developer Myself.",
        "",
        "## Como funciona",
        "",
        f"- **Até {max_in_progress} conteúdos em andamento**, cada um de uma competência "
        "diferente. Quando abre uma vaga, entra o da fila que mais se interliga com os outros.",
        "- **Cada pomodoro pontuado** (25 min + anotações) conclui **1 dia** do cronograma "
        "de 30 dias do conteúdo.",
        "- **Dias 1 a 10:** fundamentos + 3 desafios de Intermediário. No Intermediário o "
        "conteúdo é consolidado e **abre uma vaga**.",
        "- **Dias 11 a 30:** viram **revisões** (aprofundar, laboratório, ensinar) + 3 desafios "
        "de Avançado. No dia 30 é possível **concluir**.",
        "- **Rotina diária (3h a 4h):** primeiro as revisões (a rede neural escolhe as de "
        "menor chance de lembrar), depois o estudo dos conteúdos em andamento.",
        "- **Aquecimento:** cada tópico novo volta de memória após **1, 3 e 7 dias**.",
        "- **Todo dia de estudo:** checklist de 5 perguntas sem olhar a fonte (explicar, exemplo "
        "próprio, trade-off, pergunta em aberto, nota 0 a 5; abaixo de 3, releia).",
        "",
    ]
    if week:
        out += [*week_section(week), ""]
    out += [
        "## Visão geral",
        "",
        "| # | Conteúdo | Área | Profundidade | Situação | Dia atual | Início previsto |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, item in enumerate(items, start=1):
        entry = schedule_for(item.title).entry
        day = f"{today_for(item.points)}/{TOTAL_DAYS}" if item.status != "LOCKED" else "-"
        start = starts.get(item.title) if item.status == "LOCKED" else None
        when = f"{start:%d/%m/%Y}" if start else "-"
        out.append(
            f"| {n} | [{_cell(item.title)}](#{_anchor(n)}) | {entry.area} | {entry.depth.value} "
            f"| {STATUS.get(item.status, item.status)} | {day} | {when} |"
        )
    queued = [d for t, d in starts.items() if d]
    if queued:
        out += [
            "",
            f"Projeção (simulada com as regras do sistema, supondo que toda sessão pontua): o "
            f"último conteúdo da fila começa por volta de **{max(queued):%m/%Y}**"
            + (f" e tudo chega ao Avançado por volta de **{finish:%m/%Y}**." if finish else "."),
        ]
    for n, item in enumerate(items, start=1):
        schedule = schedule_for(item.title)
        entry = schedule.entry
        current = today_for(item.points)
        out += [
            "",
            f'<a id="{_anchor(n)}"></a>',
            "",
            f"## {n}. {item.title}",
            "",
            f"**{entry.area}** · **[{entry.depth.value}]** {entry.depth.goal}",
        ]
        if entry.note:
            out += ["", f"_{entry.note}_"]
        out += ["", "| Dia | Tipo | Foco | Aquecimento de memória |", "|---|---|---|---|"]
        for d in schedule.days:
            mark = " ◀ hoje" if item.status != "LOCKED" and d.day == current else ""
            done = "✅ " if item.status != "LOCKED" and d.day < current else ""
            warm = "; ".join(d.warmup) or "-"
            out.append(
                f"| {done}{d.day}{mark} | {KIND[d.kind]} | {_cell(d.focus)} | {_cell(warm)} |"
            )
    return "\n".join(out) + "\n"


async def _main() -> None:  # pragma: no cover - depende da stack no ar
    from developer_myself.learning.domain.value_objects import ContentId  # noqa: PLC0415
    from developer_myself.mongo_bootstrap import build_mongo_container  # noqa: PLC0415
    from developer_myself.projection import project  # noqa: PLC0415
    from developer_myself.shared.adapters.mongo_setup import make_client  # noqa: PLC0415
    from developer_myself.shared.settings import Settings  # noqa: PLC0415
    from developer_myself.weekly_plan import weekly_plan  # noqa: PLC0415

    container = await build_mongo_container(Settings())
    try:
        # Uso pessoal: a (única) trilha do banco.
        settings = Settings()
        client = make_client(settings.mongo_url.get_secret_value())
        doc = await client[settings.mongo_db].study_plans.find_one({}, {"_id": 1})
        await client.close()
        if doc is None:
            raise SystemExit("Nenhuma trilha encontrada.")
        plan = await container.learning.get_plan(doc["_id"])
        now = container.clock.now()
        recommender = await container.recommender.current()
        active = [c for c in plan.contents if c.status.value != "LOCKED"]
        ordered = active + plan.queue
        items = [TrailItem(c.title.value, c.status.value, c.points.value) for c in ordered]
        today = now.astimezone(ZoneInfo(plan.timezone.name)).date()
        projection = project(plan, today)
        starts = {
            plan.content(ContentId(uuid.UUID(k))).title.value: m.started
            for k, m in projection.milestones.items()
        }
        week = weekly_plan(plan, recommender, now)
        sys.stdout.write(
            render(
                items,
                today,
                starts=starts,
                week=week,
                finish=projection.last("advanced"),
                max_in_progress=plan.unlock_policy.max_in_progress,
            )
        )
    finally:
        await container.close()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())
