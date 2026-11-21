"""Backfill do "preciso revisar" a partir do histórico de sessões."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from developer_myself.entrypoints.cli.backfill_to_review import backfill_last_to_review
from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.application.history import SessionRecord
from developer_myself.learning.adapters.memory.repository import InMemoryStudyPlanRepository
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    LearnerId,
    Timezone,
    Title,
)

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


def record(learner: uuid.UUID, content: ContentId, minutes: int, to_review: str) -> SessionRecord:
    at = NOW + timedelta(minutes=minutes)
    return SessionRecord(
        event_id=str(uuid.uuid7()),
        learner_id=str(learner),
        type="study_session_finished",
        content_id=str(content),
        content_title="x",
        kind="STUDY",
        started_at=at,
        finished_at=at,
        duration_seconds=0,
        awarded=True,
        reason=None,
        notes_studied="",
        notes_understood="",
        notes_to_review=to_review,
        level_after=None,
    )


async def setup() -> tuple[
    InMemoryStudyPlanRepository, InMemorySessionHistoryStore, StudyPlan, ContentId, ContentId
]:
    plans, history = InMemoryStudyPlanRepository(), InMemorySessionHistoryStore()
    plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
    a = plan.add_content(ContentId.new(), Title("A"), ContentKind.BOOK, NOW).id
    b = plan.add_content(ContentId.new(), Title("B"), ContentKind.BOOK, NOW).id
    await plans.save(plan)
    learner = plan.id.value
    for r in (
        record(learner, a, 1, "antigo"),
        record(learner, a, 2, "recente"),
        record(learner, a, 3, "   "),  # a mais nova está em branco: não conta
        record(learner, b, 1, ""),
        record(uuid.uuid7(), a, 9, "de outro aprendiz"),
    ):
        await history.record(r)
    return plans, history, plan, a, b


def test_fills_from_latest_non_empty_session() -> None:
    async def scenario() -> None:
        plans, history, plan, a, b = await setup()
        assert await backfill_last_to_review(plans, history, plan.id.value) == 1
        saved = await plans.get(plan.id)
        assert saved is not None
        assert saved.content(a).last_to_review == "recente"
        assert saved.content(b).last_to_review is None

    asyncio.run(scenario())


def test_keeps_existing_value() -> None:
    async def scenario() -> None:
        plans, history, plan, a, _ = await setup()
        stored = await plans.get(plan.id)
        assert stored is not None
        stored.content(a).last_to_review = "já tinha"
        await plans.save(stored)
        assert await backfill_last_to_review(plans, history, plan.id.value) == 0
        saved = await plans.get(plan.id)
        assert saved is not None
        assert saved.content(a).last_to_review == "já tinha"

    asyncio.run(scenario())


def test_idempotent_second_run_changes_nothing() -> None:
    async def scenario() -> None:
        plans, history, plan, _, _ = await setup()
        assert await backfill_last_to_review(plans, history, plan.id.value) == 1
        version = (await plans.get(plan.id)).version  # type: ignore[union-attr]
        assert await backfill_last_to_review(plans, history, plan.id.value) == 0
        assert (await plans.get(plan.id)).version == version  # type: ignore[union-attr]

    asyncio.run(scenario())


def test_unknown_learner_changes_nothing() -> None:
    async def scenario() -> None:
        plans, history, *_ = await setup()
        assert await backfill_last_to_review(plans, history, uuid.uuid7()) == 0

    asyncio.run(scenario())
