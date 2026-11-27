"""Aquecimento: GET/POST/DELETE /api/warmup e POST /api/warmup/finish.

Fica em `planning` porque escolhe o conteúdo e o próximo passo pelo ranking de revisões.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, status
from pydantic import BaseModel

from developer_myself.learning.adapters.http.schemas import FinishWarmupIn, QuestionOut
from developer_myself.learning.application.use_cases import AnswerInput
from developer_myself.learning.domain.errors import NothingToWarmUpError
from developer_myself.learning.domain.study_plan import ActiveWarmup
from developer_myself.planning.application.warmup import next_step, warmup_status, warmup_target
from developer_myself.shared.adapters.http import LearnerIdDep

router = APIRouter(prefix="/api", tags=["warmup"])


class WarmupContentOut(BaseModel):
    id: uuid.UUID
    title: str


class ActiveWarmupOut(BaseModel):
    started_at: datetime
    questions: list[QuestionOut]

    @classmethod
    def of(cls, warmup: ActiveWarmup) -> ActiveWarmupOut:
        return cls(
            started_at=warmup.started_at,
            questions=[QuestionOut.of(q) for q in warmup.questions],
        )


class WarmupStatusOut(BaseModel):
    available: bool
    done_today: bool
    content: WarmupContentOut | None
    active: ActiveWarmupOut | None


class NextStepOut(BaseModel):
    content_id: str
    title: str
    kind: str


class FinishWarmupOut(BaseModel):
    next: NextStepOut | None


async def _context(request: Request, learner_id: uuid.UUID) -> tuple[Any, Any, Any, datetime]:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    recommender = await container.recommender.current()
    return container, plan, recommender, container.clock.now()


@router.get("/warmup")
async def get_warmup(request: Request, learner_id: LearnerIdDep) -> WarmupStatusOut:
    _, plan, recommender, now = await _context(request, learner_id)
    result = warmup_status(plan, recommender, now)
    return WarmupStatusOut(
        available=result.available,
        done_today=result.done_today,
        content=(
            WarmupContentOut(id=result.target.id.value, title=result.target.title.value)
            if result.target is not None
            else None
        ),
        active=ActiveWarmupOut.of(result.active) if result.active is not None else None,
    )


@router.post("/warmup", status_code=status.HTTP_201_CREATED)
async def start_warmup(request: Request, learner_id: LearnerIdDep) -> ActiveWarmupOut:
    container, plan, recommender, now = await _context(request, learner_id)
    current = plan.current_warmup(now)
    target = current.content_id if current is not None else None
    if target is None:
        chosen = warmup_target(plan, recommender, now)
        if chosen is None:
            raise NothingToWarmUpError("Ainda não há nada estudado para aquecer.")
        target = chosen.id
    warmup = await container.learning.start_warmup(learner_id, target.value)
    return ActiveWarmupOut.of(warmup)


@router.post("/warmup/finish")
async def finish_warmup(
    body: FinishWarmupIn, request: Request, learner_id: LearnerIdDep
) -> FinishWarmupOut:
    container = request.app.state.container
    await container.learning.finish_warmup(
        learner_id,
        [AnswerInput(a.question_id, a.answer, a.grade, a.useful) for a in body.answers],
    )
    _, plan, recommender, now = await _context(request, learner_id)
    step = next_step(plan, recommender, now)
    return FinishWarmupOut(
        next=(
            NextStepOut(content_id=step.content_id, title=step.title, kind=step.kind.value)
            if step is not None
            else None
        )
    )


@router.delete("/warmup", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_warmup(request: Request, learner_id: LearnerIdDep) -> None:
    await request.app.state.container.learning.cancel_warmup(learner_id)
