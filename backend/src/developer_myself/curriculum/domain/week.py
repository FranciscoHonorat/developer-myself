"""Semana planejada: 7 dias, cada um com 3 ou 4 competências (mais o hábito diário) e o
tempo escolhido.

Unidade: o **pomodoro de 30 min** (25 de estudo + 5 de pausa), então de 180 a 480
minutos viram de 6 a 16 pomodoros, sem sobra. Em cada dia de estudo:

1. **Revisões primeiro** (2 pomodoros), em conteúdos consolidados escolhidos pela rede
   neural e em rodízio ao longo da semana. Revisar antes libera a pontuação do estudo.
2. **Hábito diário** (ex.: Inglês): 2 pomodoros todo dia, logo depois das revisões.
3. **Estudo**: o resto vai para os até 3 conteúdos em andamento, em rodízio (o pomodoro
   extra muda de conteúdo a cada dia), então todos aparecem em todos os dias.
4. No máximo **4 competências por dia** fora o hábito diário: uma revisão que traria a 5ª
   competência cede a vez para mais um pomodoro na revisão anterior.

Cada pomodoro pontuado avança 1 dia no cronograma de 30 dias do conteúdo, e a semana
acompanha isso: um bloco que cobre um dia de desafio vira bloco de desafio.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum

from developer_myself.curriculum.domain.schedule import TOTAL_DAYS, DayKind, Schedule

POMODORO_MINUTES = 30
STUDY_MINUTES = 25
REVIEW_POMODOROS = 2
DAILY_POMODOROS = 2
MAX_COMPETENCIES_PER_DAY = 4
WEEKDAY_NAMES = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


class BlockKind(StrEnum):
    REVIEW = "REVIEW"
    STUDY = "STUDY"
    CHALLENGE = "CHALLENGE"


@dataclass(frozen=True, slots=True)
class Track:
    """Um conteúdo que entra na semana (em andamento ou para revisar)."""

    content_id: str
    title: str
    competency: str
    competency_name: str
    day: int  # dia atual no cronograma de 30 dias
    schedule: Schedule


@dataclass(frozen=True, slots=True)
class Block:
    kind: BlockKind
    track: Track
    pomodoros: int
    first_day: int
    last_day: int
    focus: str

    @property
    def minutes(self) -> int:
        return self.pomodoros * POMODORO_MINUTES


@dataclass(frozen=True, slots=True)
class WeekDay:
    date: date
    weekday: int
    is_rest: bool
    blocks: tuple[Block, ...] = ()

    @property
    def name(self) -> str:
        return WEEKDAY_NAMES[self.weekday]

    @property
    def minutes(self) -> int:
        return sum(b.minutes for b in self.blocks)

    @property
    def competencies(self) -> list[str]:
        seen: list[str] = []
        for block in self.blocks:
            if block.track.competency not in seen:
                seen.append(block.track.competency)
        return seen


@dataclass(slots=True)
class _Cursor:
    """Avanço projetado de cada conteúdo no cronograma ao longo da semana."""

    day: dict[str, int] = field(default_factory=dict)

    def take(self, track: Track, pomodoros: int, review: bool) -> Block:
        first = self.day.get(track.content_id, track.day)
        last = min(first + pomodoros - 1, TOTAL_DAYS)
        self.day[track.content_id] = min(last + 1, TOTAL_DAYS)
        span = [track.schedule.day(d) for d in range(first, last + 1)]
        challenges = [d.focus for d in span if d.kind is DayKind.CHALLENGE]
        if challenges:
            return Block(BlockKind.CHALLENGE, track, pomodoros, first, last, " + ".join(challenges))
        kind = BlockKind.REVIEW if review else BlockKind.STUDY
        return Block(kind, track, pomodoros, first, last, span[0].focus)


def _review_blocks(
    reviews: list[Track],
    index: int,
    budget: int,
    taken: list[str],
    cursor: _Cursor,
    *,
    max_picks: int,
) -> list[Block]:
    if not reviews or budget <= 0:
        return []
    picks: list[Track] = []
    for offset in range(len(reviews)):
        track = reviews[(index + offset) % len(reviews)]  # rodízio: 1 posição por dia
        comps = set(taken) | {p.competency for p in picks}
        fits = track.competency in comps or len(comps) < MAX_COMPETENCIES_PER_DAY
        if fits and track not in picks:
            picks.append(track)
        if len(picks) == min(budget, max_picks):
            break
    if not picks:  # nenhuma revisão cabe sem passar de 4 competências no dia
        return []
    share = [budget // len(picks)] * len(picks)
    for i in range(budget % len(picks)):
        share[i] += 1
    return [cursor.take(t, n, review=True) for t, n in zip(picks, share, strict=True) if n]


def _study_blocks(study: list[Track], index: int, budget: int, cursor: _Cursor) -> list[Block]:
    if not study or budget <= 0:
        return []
    share = [budget // len(study)] * len(study)
    for i in range(budget % len(study)):
        share[(index + i) % len(study)] += 1  # o pomodoro extra roda entre os conteúdos
    return [cursor.take(t, n, review=False) for t, n in zip(study, share, strict=True) if n]


def build_week(
    study: list[Track],
    reviews: list[Track],
    *,
    minutes_per_day: int,
    rest_days: frozenset[int],
    start: date,
    daily: list[Track] | None = None,
) -> list[WeekDay]:
    pomodoros = minutes_per_day // POMODORO_MINUTES
    study = study[: MAX_COMPETENCIES_PER_DAY - 1]
    cursor = _Cursor()
    days: list[WeekDay] = []
    active_index = 0
    for offset in range(7):
        current = start + timedelta(days=offset)
        weekday = current.weekday()
        if weekday in rest_days:
            days.append(WeekDay(current, weekday, is_rest=True))
            continue
        minimum = min(REVIEW_POMODOROS, pomodoros)
        reserved = DAILY_POMODOROS * len(daily or [])  # sem estudo, o hábito diário fica
        review_budget = minimum if study else max(pomodoros - reserved, minimum)
        taken = [t.competency for t in study]
        max_picks = REVIEW_POMODOROS if study else MAX_COMPETENCIES_PER_DAY
        blocks = _review_blocks(
            reviews, active_index, review_budget, taken, cursor, max_picks=max_picks
        )
        for track in daily or []:
            left = pomodoros - sum(b.pomodoros for b in blocks)
            if left > 0:
                blocks.append(cursor.take(track, min(DAILY_POMODOROS, left), review=False))
        used = sum(b.pomodoros for b in blocks)
        blocks += _study_blocks(study, active_index, pomodoros - used, cursor)
        days.append(WeekDay(current, weekday, is_rest=False, blocks=tuple(blocks)))
        active_index += 1
    return days
