"""GET /api/competencies: a ficha de competências (gamificação)."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from developer_myself.curriculum.domain.progression import (
    DECAY_PER_DAY,
    FRESHNESS_FLOOR,
    GRACE_DAYS,
    CompetencyScore,
)
from developer_myself.planning.application.competency_sheet import competency_sheet
from developer_myself.shared.adapters.http import LearnerIdDep

router = APIRouter(prefix="/api", tags=["curriculum"])


class ContributionOut(BaseModel):
    title: str
    progress: float
    freshness: float
    rust_in_days: int | None


class CompetencyOut(BaseModel):
    key: str
    name: str
    area: str
    score: float
    peak: float
    rust_lost: float
    tier: str
    title: str
    target: str | None
    target_score: int | None
    points: float
    status: str
    rust_in_days: int | None
    contents: list[ContributionOut]

    @classmethod
    def of(cls, s: CompetencyScore) -> CompetencyOut:
        target = s.competency.target
        return cls(
            key=s.competency.key,
            name=s.competency.name,
            area=s.competency.area.value,
            score=s.score,
            peak=s.peak,
            rust_lost=round(s.rust_lost, 1),
            tier=s.tier.value,
            title=s.title,
            target=target.value if target else None,
            target_score=target.floor if target else None,
            points=round(s.points, 1),
            status=s.status,
            rust_in_days=s.rust_in_days,
            contents=[
                ContributionOut(
                    title=c.title,
                    progress=round(c.progress, 3),
                    freshness=round(c.freshness, 3),
                    rust_in_days=c.rust_in_days,
                )
                for c in s.contents
            ],
        )


class EffortOut(BaseModel):
    area: str
    points: float


class RulesOut(BaseModel):
    grace_days: int = GRACE_DAYS
    decay_per_day: float = DECAY_PER_DAY
    floor: float = FRESHNESS_FLOOR


class SheetOut(BaseModel):
    xp: int
    level: int
    next_level_xp: int
    total_points: float
    competencies: list[CompetencyOut]
    effort: list[EffortOut]
    rules: RulesOut


@router.get("/competencies")
async def competencies(request: Request, learner_id: LearnerIdDep) -> SheetOut:
    container = request.app.state.container
    plan = await container.learning.get_plan(learner_id)
    sheet = competency_sheet(plan, container.clock.now())
    return SheetOut(
        xp=sheet.xp,
        level=sheet.level,
        next_level_xp=sheet.next_level_xp,
        total_points=round(sheet.total_points, 1),
        competencies=[CompetencyOut.of(s) for s in sheet.competencies],
        effort=[EffortOut(area=a.area.value, points=round(a.points, 1)) for a in sheet.effort],
        rules=RulesOut(),
    )
