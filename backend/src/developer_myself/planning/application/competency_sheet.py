"""Monta a ficha de competências a partir da trilha (learning) + catálogo (curriculum)."""

from datetime import datetime

from developer_myself.curriculum.application.schedules import schedule_for
from developer_myself.curriculum.domain.competencies import skills_for
from developer_myself.curriculum.domain.progression import ContentSnapshot, Sheet, build_sheet
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import MasteryLevel


def snapshot(content: Content) -> ContentSnapshot:
    solved = [c for c in content.challenges if c.solved_at is not None]
    activity = [content.last_session_at, *(c.solved_at for c in solved)]
    known = [moment for moment in activity if moment is not None]
    return ContentSnapshot(
        title=content.title.value,
        points=content.points.value,
        intermediate_solved=sum(c.target_level is MasteryLevel.INTERMEDIATE for c in solved),
        advanced_solved=sum(c.target_level is MasteryLevel.ADVANCED for c in solved),
        last_activity=max(known) if known else None,
        depth=schedule_for(content.title.value).entry.depth,
        skills=skills_for(content.title.value),
    )


def competency_sheet(plan: StudyPlan, now: datetime) -> Sheet:
    return build_sheet((snapshot(c) for c in plan.contents), now)
