from datetime import UTC, datetime

from developer_myself.curriculum.domain.unlock import (
    CatalogUnlockPolicy,
    affinity,
    primary_competency,
)
from developer_myself.learning.domain.policies import SingleTrackUnlockPolicy
from developer_myself.learning.domain.study_plan import StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentId,
    ContentKind,
    ContentStatus,
    LearnerId,
    Timezone,
    Title,
)

NOW = datetime(2026, 11, 2, tzinfo=UTC)


def test_single_track_policy_is_the_domain_default() -> None:
    policy = SingleTrackUnlockPolicy()
    assert policy.max_in_progress == 1
    assert policy.competency_of("qualquer") == "trilha"
    assert policy.affinity("a", "b") == 0.0
    plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
    assert isinstance(plan.unlock_policy, SingleTrackUnlockPolicy)


def test_refresh_queue_fills_new_slots_when_policy_grows() -> None:
    plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
    for title in ("Linux", "Learning Go", "SAST/DAST/SCA", "Redes"):
        plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)
    assert [c.title.value for c in plan.in_progress_contents] == ["Linux"]

    plan.unlock_policy = CatalogUnlockPolicy(max_in_progress=3)
    unlocked = plan.refresh_queue(NOW)
    # Com Linux (fundamentos) em andamento, SAST (appsec, afinidade 0,5 com fundamentos)
    # passa à frente de Learning Go (sem afinidade), apesar de ter chegado depois.
    assert [plan.content(i).title.value for i in unlocked] == ["SAST/DAST/SCA", "Learning Go"]
    assert plan.find_by_title("Redes").status is ContentStatus.LOCKED  # type: ignore[union-attr]
    assert plan.refresh_queue(NOW) == []


def test_primary_competency_and_affinity() -> None:
    assert primary_competency("Learning Go") == "go"
    assert primary_competency("Gin") == "backend"  # empate 50/50: a primeira listada
    assert primary_competency("Livro desconhecido") == "outros"
    assert affinity("go", "backend") == affinity("backend", "go") == 1.0
    assert affinity("go", "devops") == 0.5
    assert affinity("go", "go") == 0.0
    assert affinity("ingles", "dfir") == 0.0


def test_reorder_queue_validations_and_event() -> None:
    import pytest  # noqa: PLC0415

    from developer_myself.learning.domain.errors import (  # noqa: PLC0415
        ContentNotFoundError,
        InvalidValueError,
    )
    from developer_myself.learning.domain.events import QueueReordered  # noqa: PLC0415

    plan = StudyPlan.create(LearnerId.new(), Timezone("UTC"))
    ids = [plan.add_content(ContentId.new(), Title(t), ContentKind.BOOK, NOW).id for t in "ABC"]
    plan.pull_events()
    with pytest.raises(InvalidValueError):
        plan.reorder_queue([ids[1], ids[1]], NOW)
    with pytest.raises(ContentNotFoundError):
        plan.reorder_queue([ContentId.new()], NOW)
    plan.reorder_queue([ids[2]], NOW)
    assert [c.title.value for c in plan.queue] == ["C", "B"]
    (event,) = plan.pull_events()
    assert isinstance(event, QueueReordered)
    assert event.order == (ids[2].value, ids[1].value)
