"""Motor de simulação compartilhado pela semana planejada e pela projeção de datas.

`day_blocks` monta o dia a partir do estado ATUAL da trilha; `play` executa esse dia nas
regras REAIS do domínio (cada pomodoro vira uma sessão pontuada; os desafios de cada nível
são resolvidos ao atingir os pontos; no Avançado o conteúdo é concluído). Assim, a semana
e a projeção enxergam consolidações e vagas abrindo no meio do caminho.
"""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.competencies import BY_KEY
from developer_myself.curriculum.domain.schedule import TOTAL_DAYS, today_for
from developer_myself.curriculum.domain.unlock import primary_competency
from developer_myself.curriculum.domain.week import STUDY_MINUTES, Track, WeekDay, build_week
from developer_myself.insights.application.recommender import ReviewRecommender, rank
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    ContentStatus,
    Evidence,
    MasteryLevel,
    Notes,
    RecallRating,
    SessionKind,
)
from developer_myself.review_candidates import review_candidates

NOTES = Notes("estudo simulado " * 3, "entendimento simulado " * 2, "revisar simulado " * 2)
LEVEL_POINTS = {MasteryLevel.INTERMEDIATE: 10, MasteryLevel.ADVANCED: 30}
CHALLENGES_PER_LEVEL = 3
PAUSE = timedelta(minutes=5)
OnProgress = Callable[[Content, date], None]


def track_for(content: Content) -> Track:
    key = primary_competency(content.title.value)
    return Track(
        content_id=str(content.id),
        title=content.title.value,
        competency=key,
        competency_name=BY_KEY[key].name,
        day=today_for(content.points.value),
        schedule=schedule_for(content.title.value),
    )


def local_day(plan: StudyPlan, now: datetime) -> date:
    return now.astimezone(ZoneInfo(plan.timezone.name)).date()


def morning(plan: StudyPlan, day: date) -> datetime:
    return datetime.combine(day, time(8, 0), tzinfo=ZoneInfo(plan.timezone.name))


def day_blocks(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> WeekDay:
    """O dia de hoje montado a partir do estado atual da trilha."""
    study = sorted(plan.in_progress_contents, key=lambda c: c.queued_at)
    pending = {
        str(c.id): c
        for c in plan.contents
        if c.status is ContentStatus.CONSOLIDATED and c.points.value < TOTAL_DAYS
    }
    ranked = rank(recommender, [c for c in review_candidates(plan, now) if c.content_id in pending])
    return build_week(
        [track_for(c) for c in study],
        [track_for(pending[r.content_id]) for r in ranked],
        minutes_per_day=plan.preferences.minutes_per_day,
        rest_days=plan.preferences.rest_days,
        start=local_day(plan, now),
    )[0]


def _solve_level(plan: StudyPlan, content: Content, level: MasteryLevel, now: datetime) -> None:
    solved = sum(1 for lvl in content.solved_challenge_levels if lvl is level)
    for _ in range(CHALLENGES_PER_LEVEL - solved):
        challenge = plan.add_challenge(content.id, ChallengeId.new(), "simulado", level, now)
        plan.solve_challenge(content.id, challenge.id, Evidence("simulação"), now)


def play(sim: StudyPlan, day: WeekDay, on_progress: OnProgress | None = None) -> None:
    """Executa os blocos do dia na trilha simulada (que é alterada)."""
    now = morning(sim, day.date)
    for block in day.blocks:
        content = sim.content(ContentId.from_str(block.track.content_id))
        for _ in range(block.pomodoros):
            if content.status is ContentStatus.FINISHED:
                break
            kind = sim.start_session(content.id, now)
            now += timedelta(minutes=STUDY_MINUTES)
            rating = RecallRating.GOOD if kind is SessionKind.REVIEW else None
            sim.finish_session(NOTES, now, rating)
            now += PAUSE
            if content.points.value >= LEVEL_POINTS[MasteryLevel.INTERMEDIATE]:
                _solve_level(sim, content, MasteryLevel.INTERMEDIATE, now)
            if content.points.value >= LEVEL_POINTS[MasteryLevel.ADVANCED]:
                _solve_level(sim, content, MasteryLevel.ADVANCED, now)
                sim.finish_content(content.id, now)
            if on_progress is not None:
                on_progress(content, day.date)
    sim.pull_events()
