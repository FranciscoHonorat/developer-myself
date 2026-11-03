"""Plano de hoje: compõe a trilha (learning), os cronogramas (curriculum) e a rede
neural (insights) — só por dados, nenhum contexto importa o modelo do outro além daqui.

- Estudo: os conteúdos em andamento (até 3), cada um no dia `pontos + 1` do cronograma.
- Revisões: conteúdos consolidados ainda abaixo de 30 pontos, na ordem da rede neural
  (menor chance de lembrar primeiro). Revisar antes de estudar libera a pontuação do dia.
"""

from dataclasses import dataclass
from datetime import datetime

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.schedule import TOTAL_DAYS, DayPlan, Schedule, today_for
from developer_myself.insights.application.recommender import ReviewRecommender, rank
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import ContentStatus
from developer_myself.review_candidates import review_candidates

MAX_REVIEWS_PER_DAY = 2


@dataclass(frozen=True, slots=True)
class DailyItem:
    content_id: str
    title: str
    day: int
    schedule: Schedule

    @property
    def plan(self) -> DayPlan:
        return self.schedule.day(self.day)


@dataclass(frozen=True, slots=True)
class DailyPlan:
    studies: list[DailyItem]
    reviews: list[DailyItem]


def item_for(content: Content) -> DailyItem:
    return DailyItem(
        content_id=str(content.id),
        title=content.title.value,
        day=today_for(content.points.value),
        schedule=schedule_for(content.title.value),
    )


def daily_plan(plan: StudyPlan, recommender: ReviewRecommender, now: datetime) -> DailyPlan:
    current = sorted(plan.in_progress_contents, key=lambda c: c.queued_at)
    pending = {
        str(c.id): c
        for c in plan.contents
        if c.status is ContentStatus.CONSOLIDATED and c.points.value < TOTAL_DAYS
    }
    ranked = rank(recommender, [c for c in review_candidates(plan, now) if c.content_id in pending])
    reviews = [item_for(pending[r.content_id]) for r in ranked[:MAX_REVIEWS_PER_DAY]]
    return DailyPlan(studies=[item_for(c) for c in current], reviews=reviews)
