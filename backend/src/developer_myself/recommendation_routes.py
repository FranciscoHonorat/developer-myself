"""GET /api/recommendations: conteúdos para revisar, do mais "esquecido" ao mais fresco."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from developer_myself.insights.application.recommender import rank
from developer_myself.review_candidates import review_candidates
from developer_myself.shared.adapters.http import LearnerIdDep

router = APIRouter(prefix="/api", tags=["insights"])


class RecommendationOut(BaseModel):
    content_id: str
    title: str
    recall_probability: float


class ModelInfoOut(BaseModel):
    trained_on: str | None = None
    trained_at: str | None = None
    real_samples: int = 0


class RecommendationsOut(BaseModel):
    model: str
    model_info: ModelInfoOut
    items: list[RecommendationOut]


@router.get("/recommendations")
async def recommendations(request: Request, learner_id: LearnerIdDep) -> RecommendationsOut:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    recommender = await container.recommender.current()
    ranked = rank(recommender, review_candidates(plan, container.clock.now()))
    meta = recommender.metadata
    return RecommendationsOut(
        model=recommender.name,
        model_info=ModelInfoOut(
            trained_on=str(meta["trained_on"]) if "trained_on" in meta else None,
            trained_at=str(meta["trained_at"]) if "trained_at" in meta else None,
            real_samples=int(str(meta.get("real_samples", 0))),
        ),
        items=[
            RecommendationOut(
                content_id=r.content_id,
                title=r.title,
                recall_probability=round(r.recall_probability, 3),
            )
            for r in ranked
        ],
    )
