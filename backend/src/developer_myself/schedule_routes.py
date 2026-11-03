"""Cronograma diário: GET /api/today e GET /api/contents/{id}/schedule."""

import uuid
from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.schedule import TOTAL_DAYS, DayPlan, today_for
from developer_myself.curriculum.domain.week import (
    POMODORO_MINUTES,
    STUDY_MINUTES,
    Block,
    WeekDay,
)
from developer_myself.daily_plan import DailyItem, daily_plan
from developer_myself.learning.domain.value_objects import ContentId
from developer_myself.shared.adapters.http import LearnerIdDep
from developer_myself.weekly_plan import weekly_plan

router = APIRouter(prefix="/api", tags=["curriculum"])


class DayOut(BaseModel):
    day: int
    phase: str
    kind: str
    focus: str
    activity: str
    warmup: list[str]
    target_level: str | None
    done: bool = False

    @classmethod
    def of(cls, d: DayPlan, current_day: int) -> DayOut:
        return cls(
            day=d.day,
            phase=d.phase.value,
            kind=d.kind.value,
            focus=d.focus,
            activity=d.activity,
            warmup=list(d.warmup),
            target_level=d.target_level,
            done=d.day < current_day,
        )


class TodayItemOut(BaseModel):
    content_id: str
    title: str
    day: int
    total_days: int
    plan: DayOut

    @classmethod
    def of(cls, item: DailyItem) -> TodayItemOut:
        return cls(
            content_id=item.content_id,
            title=item.title,
            day=item.day,
            total_days=TOTAL_DAYS,
            plan=DayOut.of(item.plan, item.day),
        )


class BlockOut(BaseModel):
    kind: str
    content_id: str
    title: str
    competency: str
    competency_name: str
    pomodoros: int
    minutes: int
    first_day: int
    last_day: int
    focus: str

    @classmethod
    def of(cls, b: Block) -> BlockOut:
        return cls(
            kind=b.kind.value,
            content_id=b.track.content_id,
            title=b.track.title,
            competency=b.track.competency,
            competency_name=b.track.competency_name,
            pomodoros=b.pomodoros,
            minutes=b.minutes,
            first_day=b.first_day,
            last_day=b.last_day,
            focus=b.focus,
        )


class WeekDayOut(BaseModel):
    date: date
    weekday: int
    name: str
    is_rest: bool
    minutes: int
    competencies: list[str]
    blocks: list[BlockOut]

    @classmethod
    def of(cls, d: WeekDay) -> WeekDayOut:
        return cls(
            date=d.date,
            weekday=d.weekday,
            name=d.name,
            is_rest=d.is_rest,
            minutes=d.minutes,
            competencies=d.competencies,
            blocks=[BlockOut.of(b) for b in d.blocks],
        )


class WeekOut(BaseModel):
    minutes_per_day: int
    rest_days: list[int]
    pomodoro_minutes: int = POMODORO_MINUTES
    study_minutes: int = STUDY_MINUTES
    days: list[WeekDayOut]


class TodayOut(BaseModel):
    studies: list[TodayItemOut]
    reviews: list[TodayItemOut]
    blocks: list[BlockOut]


class ScheduleOut(BaseModel):
    content_id: str
    title: str
    area: str
    depth: str
    depth_goal: str
    from_map: bool
    note: str
    current_day: int
    total_days: int
    days: list[DayOut]


@router.get("/today")
async def today(request: Request, learner_id: LearnerIdDep) -> TodayOut:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    recommender = await container.recommender.current()
    now = container.clock.now()
    result = daily_plan(plan, recommender, now)
    today_blocks = weekly_plan(plan, recommender, now)[0].blocks
    return TodayOut(
        studies=[TodayItemOut.of(s) for s in result.studies],
        reviews=[TodayItemOut.of(r) for r in result.reviews],
        blocks=[BlockOut.of(b) for b in today_blocks],
    )


@router.get("/week")
async def week(request: Request, learner_id: LearnerIdDep) -> WeekOut:
    """Os próximos 7 dias, a partir de hoje: blocos de revisão e de estudo por competência."""
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    recommender = await container.recommender.current()
    days = weekly_plan(plan, recommender, container.clock.now())
    return WeekOut(
        minutes_per_day=plan.preferences.minutes_per_day,
        rest_days=sorted(plan.preferences.rest_days),
        days=[WeekDayOut.of(d) for d in days],
    )


@router.get("/contents/{content_id}/schedule")
async def schedule(
    request: Request, content_id: uuid.UUID, learner_id: LearnerIdDep
) -> ScheduleOut:
    plan = await request.app.state.container.learning.get_plan(learner_id)
    content = plan.content(ContentId(content_id))
    sched = schedule_for(content.title.value)
    current = today_for(content.points.value)
    return ScheduleOut(
        content_id=str(content.id),
        title=content.title.value,
        area=sched.entry.area,
        depth=sched.entry.depth.value,
        depth_goal=sched.entry.depth.goal,
        from_map=sched.entry.from_map,
        note=sched.entry.note,
        current_day=current,
        total_days=TOTAL_DAYS,
        days=[DayOut.of(d, current) for d in sched.days],
    )
