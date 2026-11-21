"""Leitura do histórico, estatísticas e exportação de dados (LGPD)."""

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from developer_myself.insights.application.history import (
    HistoryCursor,
    HistoryQueries,
    SessionRecord,
)
from developer_myself.shared.adapters.cursor import decode_cursor, encode_cursor
from developer_myself.shared.adapters.http import LearnerIdDep


class RecallItemOut(BaseModel):
    text: str
    source: str
    answer: str
    grade: str
    useful: bool | None


class SessionOut(BaseModel):
    event_id: str
    type: str
    content_id: str
    content_title: str
    kind: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    awarded: bool
    reason: str | None
    notes_studied: str
    notes_understood: str
    notes_to_review: str
    level_after: str | None
    recall_rating: int | None = None
    recall_test: list[RecallItemOut] = []

    @classmethod
    def of(cls, r: SessionRecord) -> SessionOut:
        return cls(
            event_id=r.event_id,
            type=r.type,
            content_id=r.content_id,
            content_title=r.content_title,
            kind=r.kind,
            started_at=r.started_at,
            finished_at=r.finished_at,
            duration_seconds=r.duration_seconds,
            awarded=r.awarded,
            reason=r.reason,
            notes_studied=r.notes_studied,
            notes_understood=r.notes_understood,
            notes_to_review=r.notes_to_review,
            level_after=r.level_after,
            recall_rating=r.recall_rating,
            recall_test=[
                RecallItemOut(
                    text=i["text"],
                    source=i["source"],
                    answer=i["answer"],
                    grade=i["grade"],
                    useful=i["useful"],
                )
                for i in r.recall_test
            ],
        )


class DailyOut(BaseModel):
    day: date
    sessions: int
    minutes: int
    points: int


class StatsOut(BaseModel):
    total_sessions: int
    total_points: int
    total_minutes: int
    current_streak_days: int
    withheld_by_reason: dict[str, int]
    daily: list[DailyOut]


def get_history(request: Request) -> HistoryQueries:
    q: HistoryQueries = request.app.state.container.history
    return q


History = Annotated[HistoryQueries, Depends(get_history)]
router = APIRouter(prefix="/api", tags=["insights"])


class HistoryPageOut(BaseModel):
    items: list[SessionOut]
    # Opaco para o cliente: é só devolver em `?cursor=` para pedir a página seguinte.
    next_cursor: str | None


@router.get("/history")
async def history(
    learner_id: LearnerIdDep,
    q: History,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> HistoryPageOut:
    after = HistoryCursor(*decode_cursor(cursor)) if cursor else None
    page = await q.page(learner_id, limit, after)
    return HistoryPageOut(
        items=[SessionOut.of(r) for r in page.items],
        next_cursor=(
            encode_cursor(page.next.finished_at, page.next.event_id) if page.next else None
        ),
    )


@router.get("/stats")
async def stats(
    request: Request,
    learner_id: LearnerIdDep,
    q: History,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> StatsOut:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    s = await q.stats(learner_id, plan.timezone.name, container.clock.now(), days)
    return StatsOut(
        total_sessions=s.total_sessions,
        total_points=s.total_points,
        total_minutes=s.total_minutes,
        current_streak_days=s.current_streak_days,
        withheld_by_reason=s.withheld_by_reason,
        daily=[
            DailyOut(day=d.day, sessions=d.sessions, minutes=d.minutes, points=d.points)
            for d in s.daily
        ],
    )
