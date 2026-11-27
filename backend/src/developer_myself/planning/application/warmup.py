"""Aquecimento na tela Hoje: qual conteúdo aquecer e qual o próximo passo depois.

Fica em `planning` (compositor) porque usa o ranking de revisões do `ReviewRecommender`;
o domínio (`learning`) só garante a elegibilidade e as regras do aquecimento.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from developer_myself.curriculum.domain.schedule import TOTAL_DAYS
from developer_myself.insights.application.recommender import ReviewRecommender, rank
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import ActiveWarmup, StudyPlan
from developer_myself.learning.domain.value_objects import ContentId, ContentStatus, SessionKind
from developer_myself.planning.application.daily_plan import daily_plan
from developer_myself.planning.application.review_candidates import review_candidates


@dataclass(frozen=True, slots=True)
class NextStep:
    content_id: str
    title: str
    kind: SessionKind


@dataclass(frozen=True, slots=True)
class WarmupStatus:
    available: bool
    done_today: bool
    target: Content | None
    active: ActiveWarmup | None


def _review_ranking(
    plan: StudyPlan, recommender: ReviewRecommender, now: datetime
) -> list[Content]:
    """Mesmo filtro e ordem das revisões da tela Hoje (sem o corte de 2 por dia)."""
    pending = {
        str(c.id): c
        for c in plan.contents
        if c.status is ContentStatus.CONSOLIDATED and c.points.value < TOTAL_DAYS
    }
    candidates = [c for c in review_candidates(plan, now) if c.content_id in pending]
    return [pending[r.content_id] for r in rank(recommender, candidates)]


def warmup_target(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> Content | None:
    studying = [c for c in plan.in_progress_contents if plan.can_warm_up(c)]
    if studying:
        return max(studying, key=lambda c: c.last_session_at or c.queued_at)
    return next((c for c in _review_ranking(plan, recommender, now) if plan.can_warm_up(c)), None)


def next_step(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> NextStep | None:
    """O mesmo próximo passo da tela Hoje (`frontend/src/features/today/day.ts:dayItems`):
    revisões antes de estudos, pulando o que já foi feito hoje (sessão hoje no conteúdo, ou
    revisão do dia já feita)."""
    day = daily_plan(plan, recommender, now)
    today = plan.timezone.local_date(now)
    reviewed = plan.reviewed_today(now)

    def done(content_id: str, kind: SessionKind) -> bool:
        content = plan.content(ContentId(uuid.UUID(content_id)))
        touched = content.last_session_at is not None and (
            plan.timezone.local_date(content.last_session_at) == today
        )
        return touched or (kind is SessionKind.REVIEW and reviewed)

    ordered = [(i, SessionKind.REVIEW) for i in day.reviews] + [
        (i, SessionKind.STUDY) for i in day.studies
    ]
    for item, kind in ordered:
        if not done(item.content_id, kind):
            return NextStep(content_id=item.content_id, title=item.title, kind=kind)
    return None


def warmup_status(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> WarmupStatus:
    done = plan.warmed_up_today(now)
    target = warmup_target(plan, recommender, now)
    return WarmupStatus(
        available=target is not None and not done and plan.active_session is None,
        done_today=done,
        target=target,
        active=plan.current_warmup(now),
    )
