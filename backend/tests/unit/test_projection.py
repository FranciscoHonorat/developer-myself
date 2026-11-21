"""A projeção usa as regras reais do domínio: as datas precisam bater com a conta à mão."""

from datetime import UTC, date, datetime, timedelta

from developer_myself.curriculum.domain.unlock import CatalogUnlockPolicy
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    ContentStatus,
    LearnerId,
    StudyPreferences,
    Timezone,
    Title,
)
from developer_myself.planning.application.projection import project

TODAY = date(2026, 11, 2)


def plan_with(*titles: str, minutes: int = 240) -> StudyPlan:
    plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
    plan.unlock_policy = CatalogUnlockPolicy(3)
    plan.preferences = StudyPreferences(minutes, frozenset())
    for title in titles:
        plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, datetime.now(UTC))
    plan.pull_events()
    return plan


def test_single_content_reaches_intermediate_then_advanced() -> None:
    # 1 conteúdo, 8 pomodoros/dia: 10 pontos em 2 dias; os outros 20 só como revisão.
    result = project(plan_with("Linux"), TODAY)
    (m,) = result.milestones.values()
    assert m.started == TODAY
    assert m.intermediate == TODAY + timedelta(days=1)
    assert m.advanced is not None
    assert m.advanced > m.intermediate
    assert result.finished_all


def test_queue_waits_for_a_slot_of_the_same_competency() -> None:
    result = project(plan_with("Linux", "Redes"), TODAY)
    linux, redes = result.milestones.values()
    assert redes.started is not None
    assert linux.intermediate is not None
    assert redes.started >= linux.intermediate  # mesma competência: só depois do Intermediário


def test_simulation_does_not_touch_the_real_plan() -> None:
    plan = plan_with("Linux")
    project(plan, TODAY, max_days=3)
    assert plan.contents[0].points.value == 0
    assert plan.contents[0].status is ContentStatus.IN_PROGRESS
    assert plan.pending_events == ()


def test_stops_at_max_days() -> None:
    result = project(plan_with("Linux", minutes=60), TODAY, max_days=2)
    assert result.days == 2
    assert not result.finished_all
