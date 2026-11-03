"""Rotas que compõem vários contextos (só por IDs): exportação de dados (LGPD, ADR-0009)."""

from typing import Any

from fastapi import APIRouter, Request

from developer_myself.identity.domain.model import UserId
from developer_myself.insights.adapters.http_routes import SessionOut
from developer_myself.learning.adapters.http.schemas import PlanOut
from developer_myself.shared.adapters.http import LearnerIdDep

router = APIRouter(prefix="/api", tags=["account"])


@router.get("/export")
async def export(request: Request, learner_id: LearnerIdDep) -> dict[str, Any]:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    me = await container.identity.me(UserId(learner_id))
    history = await container.history.recent(learner_id, 100_000)
    return {
        "account": {"id": str(me.id.value), "email": me.email.value, "created_at": me.created_at},
        "plan": PlanOut.of(plan, container.clock.now()).model_dump(mode="json"),
        "history": [SessionOut.of(r).model_dump(mode="json") for r in history],
    }
