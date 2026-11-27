"""Casos de borda do agregado que os cenários BDD não cobrem."""

from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.curriculum.domain.unlock import CatalogUnlockPolicy
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.errors import (
    ChallengeNotFoundError,
    ContentLockedError,
    ContentNotFoundError,
    DuplicateContentError,
    InvalidTransitionError,
    InvalidValueError,
    MasteryNotReachedError,
    NoActiveSessionError,
    SessionAlreadyActiveError,
)
from developer_myself.learning.domain.events import (
    ContentAdded,
    ContentPurposeChanged,
    ContentQueued,
    ContentRemoved,
    ContentRenamed,
    ContentUnlocked,
    PlanPurposeChanged,
    StudyPreferencesChanged,
    StudySessionFinished,
)
from developer_myself.learning.domain.study_plan import (
    MAX_CHALLENGES_PER_CONTENT,
    MAX_CONTENTS,
    StudyPlan,
)
from developer_myself.learning.domain.value_objects import (
    PURPOSE_MAX_LENGTH,
    ChallengeId,
    ContentId,
    ContentKind,
    ContentStatus,
    Evidence,
    LearnerId,
    MasteryLevel,
    Notes,
    Points,
    Purpose,
    RecallRating,
    SessionKind,
    StudyPreferences,
    Timezone,
    Title,
)

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)
NOTES = Notes("a" * 20, "b" * 20, "c" * 20)


@pytest.fixture
def plan() -> StudyPlan:
    return StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))


def master(plan: StudyPlan, content: Content) -> None:
    """Leva o conteúdo ao nível máximo: 30 pontos + 3 desafios de cada nível."""
    content.points = Points(30)  # atalho de teste; em produção só `finish_session` muda pontos
    for level in (MasteryLevel.INTERMEDIATE, MasteryLevel.ADVANCED):
        for _ in range(3):
            ch = plan.add_challenge(content.id, ChallengeId.new(), "desafio", level, NOW)
            plan.solve_challenge(content.id, ch.id, Evidence("https://github.com/x"), NOW)
    assert plan.level_of(content) is MasteryLevel.ADVANCED


def add(plan: StudyPlan, title: str) -> Content:
    return plan.add_content(ContentId.new(), Title(title), ContentKind.BOOK, NOW)


def test_add_records_events_in_order(plan: StudyPlan) -> None:
    add(plan, "A")
    add(plan, "B")
    types = [type(e) for e in plan.pull_events()]
    assert types == [ContentAdded, ContentUnlocked, ContentAdded, ContentQueued]
    assert plan.pull_events() == []


def test_duplicate_title_is_rejected_case_insensitively(plan: StudyPlan) -> None:
    add(plan, "Clean Code")
    with pytest.raises(DuplicateContentError):
        add(plan, "clean code")


def test_unknown_content(plan: StudyPlan) -> None:
    with pytest.raises(ContentNotFoundError):
        plan.start_session(ContentId.new(), NOW)


def test_finish_or_cancel_without_session(plan: StudyPlan) -> None:
    with pytest.raises(NoActiveSessionError):
        plan.finish_session(NOTES, NOW)
    with pytest.raises(NoActiveSessionError):
        plan.cancel_session(NOW)


def test_first_session_has_no_days_since_last_contact_then_counts_days(plan: StudyPlan) -> None:
    content = add(plan, "A")
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30))
    plan.start_session(content.id, NOW + timedelta(days=3))
    plan.finish_session(NOTES, NOW + timedelta(days=3, minutes=30))
    finished = [e for e in plan.pull_events() if isinstance(e, StudySessionFinished)]
    assert [e.days_since_last_contact for e in finished] == [None, 3]
    # Para a rede: fim da última sessão → INÍCIO desta (2 dias e 23h30).
    assert finished[1].last_contact_days == pytest.approx(2 + 23.5 / 24)
    assert finished[1].session_count_before == 1
    assert content.session_count == 2
    assert content.first_session_at == NOW + timedelta(minutes=30)
    assert content.avg_notes_chars == 60
    assert finished[0].kind is SessionKind.STUDY
    assert finished[0].notes_char_count == 60


class TestChallenges:
    def test_validation(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        with pytest.raises(InvalidValueError):
            plan.add_challenge(content.id, ChallengeId.new(), "  ", MasteryLevel.INTERMEDIATE, NOW)
        with pytest.raises(InvalidValueError):
            plan.add_challenge(
                content.id, ChallengeId.new(), "x" * 2001, MasteryLevel.ADVANCED, NOW
            )
        with pytest.raises(InvalidValueError):
            plan.add_challenge(content.id, ChallengeId.new(), "ok", MasteryLevel.BEGINNER, NOW)

    def test_unknown_challenge(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        with pytest.raises(ChallengeNotFoundError):
            plan.solve_challenge(content.id, ChallengeId.new(), Evidence("x"), NOW)

    def test_cannot_solve_on_locked_content(self, plan: StudyPlan) -> None:
        add(plan, "A")
        locked = add(plan, "B")
        challenge = plan.add_challenge(
            locked.id, ChallengeId.new(), "ok", MasteryLevel.INTERMEDIATE, NOW
        )
        with pytest.raises(ContentLockedError):
            plan.solve_challenge(locked.id, challenge.id, Evidence("x"), NOW)


class TestFinishContent:
    def test_cannot_finish_with_active_session_on_it(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        plan.start_session(content.id, NOW)
        with pytest.raises(SessionAlreadyActiveError):
            plan.finish_content(content.id, NOW)

    def test_cannot_finish_locked(self, plan: StudyPlan) -> None:
        add(plan, "A")
        locked = add(plan, "B")
        with pytest.raises(InvalidTransitionError):
            plan.finish_content(locked.id, NOW)

    def test_cannot_finish_before_max_level(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        with pytest.raises(MasteryNotReachedError, match=r"atual: Iniciante"):
            plan.finish_content(content.id, NOW)
        assert content.status is ContentStatus.IN_PROGRESS

    def test_max_level_comes_from_policy(self, plan: StudyPlan) -> None:
        assert plan.max_level is MasteryLevel.ADVANCED

    def test_finishes_at_max_level_and_only_once(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        master(plan, content)
        assert plan.finish_content(content.id, NOW) is None  # fila vazia: nada a liberar
        assert content.status is ContentStatus.FINISHED
        assert content.finished_at == NOW
        with pytest.raises(InvalidTransitionError):
            plan.finish_content(content.id, NOW)


def test_content_transitions_guard(plan: StudyPlan) -> None:
    content = add(plan, "A")
    with pytest.raises(InvalidTransitionError):
        content._unlock()
    content._consolidate()
    assert content.status is ContentStatus.CONSOLIDATED
    with pytest.raises(InvalidTransitionError):
        content._consolidate()


def test_lock_reason_without_current(plan: StudyPlan) -> None:
    a = add(plan, "A")
    add(plan, "B")
    b = plan.queue[0]
    a.status = ContentStatus.FINISHED  # força estado para testar a mensagem
    assert plan.lock_reason(b) == "B está bloqueado."


def test_change_timezone(plan: StudyPlan) -> None:
    plan.change_timezone(Timezone("UTC"))
    assert plan.timezone == Timezone("UTC")
    assert not plan.reviewed_today(NOW)


def test_finishing_while_other_in_progress_unlocks_nothing(plan: StudyPlan) -> None:
    first = add(plan, "A")
    add(plan, "B")
    add(plan, "C")
    master(plan, first)  # chega a Intermediário → libera B; depois a Avançado
    assert plan.finish_content(first.id, NOW) is None
    assert plan.queue[0].title == Title("C")


def test_event_type_names_are_snake_case() -> None:
    assert StudySessionFinished.type_name() == "study_session_finished"
    assert ContentAdded.type_name() == "content_added"


def test_study_session_ignores_recall_rating(plan: StudyPlan) -> None:
    content = add(plan, "A")
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.EASY)
    finished = [e for e in plan.pull_events() if isinstance(e, StudySessionFinished)]
    assert finished[0].recall_rating is None
    assert content.review_count == 0
    assert content.last_recall_rating is None


def test_review_updates_memory_signals(plan: StudyPlan) -> None:
    content = add(plan, "A")
    content._consolidate()
    plan.start_session(content.id, NOW)
    plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.HARD)
    assert content.review_count == 1
    assert content.last_recall_rating is RecallRating.HARD
    assert RecallRating.HARD.remembered
    assert not RecallRating.FORGOT.remembered


def test_avg_notes_without_sessions_is_zero(plan: StudyPlan) -> None:
    assert add(plan, "A").avg_notes_chars == 0.0


class TestOrganize:
    def test_cannot_remove_content_with_active_session(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        plan.start_session(content.id, NOW)
        with pytest.raises(SessionAlreadyActiveError):
            plan.remove_content(content.id, NOW)

    def test_solved_challenge_counts_as_progress(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        ch = plan.add_challenge(content.id, ChallengeId.new(), "x", MasteryLevel.INTERMEDIATE, NOW)
        assert not content.has_progress
        plan.solve_challenge(content.id, ch.id, Evidence("e"), NOW)
        assert content.has_progress

    def test_remove_records_event_and_last_removal_unlocks_nothing(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        plan.pull_events()
        assert plan.remove_content(content.id, NOW) is None
        assert [type(e) for e in plan.pull_events()] == [ContentRemoved]
        assert plan.contents == []

    def test_rename_to_same_title_is_a_noop(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        plan.pull_events()
        plan.rename_content(content.id, Title("A"), NOW)
        assert plan.pull_events() == []

    def test_rename_records_event(self, plan: StudyPlan) -> None:
        content = add(plan, "• TypeScript")
        plan.pull_events()
        plan.rename_content(content.id, Title("TypeScript"), NOW)
        (event,) = plan.pull_events()
        assert isinstance(event, ContentRenamed)
        assert (event.old_title, event.new_title) == ("• TypeScript", "TypeScript")


def test_limits_on_contents_and_challenges(plan: StudyPlan) -> None:
    first = add(plan, "Conteúdo 0")
    for i in range(1, MAX_CONTENTS):
        add(plan, f"Conteúdo {i}")
    with pytest.raises(InvalidValueError, match="máximo"):
        add(plan, "Estouro")

    for i in range(MAX_CHALLENGES_PER_CONTENT):
        plan.add_challenge(
            first.id, ChallengeId.new(), f"Desafio {i}", MasteryLevel.INTERMEDIATE, NOW
        )
    with pytest.raises(InvalidValueError, match="máximo"):
        plan.add_challenge(first.id, ChallengeId.new(), "Estouro", MasteryLevel.INTERMEDIATE, NOW)


class TestSelfDetermination:
    def test_purpose_value_object_validation(self) -> None:
        p = Purpose("  Dominar AppSec  ")
        assert str(p) == "Dominar AppSec"
        with pytest.raises(InvalidValueError):
            Purpose("   ")
        with pytest.raises(InvalidValueError):
            Purpose("x" * (PURPOSE_MAX_LENGTH + 1))

    def test_plan_and_content_purpose_events(self, plan: StudyPlan) -> None:
        content = plan.add_content(
            ContentId.new(),
            Title("AppSec"),
            ContentKind.BOOK,
            NOW,
            purpose=Purpose("Proteger APIs"),
        )
        assert content.purpose == Purpose("Proteger APIs")
        plan.pull_events()

        plan.change_purpose(Purpose("Liderar arquitetura segura"), NOW)
        plan.change_purpose(Purpose("Liderar arquitetura segura"), NOW)  # no-op
        plan.change_purpose(None, NOW)
        events = plan.pull_events()
        assert [type(e) for e in events] == [PlanPurposeChanged, PlanPurposeChanged]
        assert isinstance(events[0], PlanPurposeChanged)
        assert events[0].purpose == "Liderar arquitetura segura"
        assert isinstance(events[1], PlanPurposeChanged)
        assert events[1].purpose is None

        plan.change_content_purpose(content.id, Purpose("Novo motivo"), NOW)
        plan.change_content_purpose(content.id, Purpose("Novo motivo"), NOW)  # no-op
        plan.change_content_purpose(content.id, None, NOW)
        c_events = plan.pull_events()
        assert [type(e) for e in c_events] == [ContentPurposeChanged, ContentPurposeChanged]

    def test_autonomy_parallel_slots_override_and_unlock(self) -> None:
        plan = StudyPlan.create(LearnerId.new(), Timezone("America/Sao_Paulo"))
        plan.unlock_policy = CatalogUnlockPolicy(max_in_progress=3)
        plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=1)
        assert plan.effective_max_in_progress == 1
        add(plan, "Linux")
        b = add(plan, "Learning Go")
        assert b.status is ContentStatus.LOCKED
        plan.pull_events()

        # Mesmo ritmo e mesmas vagas -> no-op
        assert (
            plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=1)
            == []
        )
        assert plan.pull_events() == []

        # Aumentar para 2 vagas libera B da fila
        unlocked = plan.change_preferences(
            StudyPreferences(210, frozenset()), NOW, max_in_progress=2
        )
        assert unlocked == [b.id]
        assert plan.content(b.id).status is ContentStatus.IN_PROGRESS
        assert any(isinstance(e, StudyPreferencesChanged) for e in plan.pull_events())

        with pytest.raises(InvalidValueError):
            plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=0)
        with pytest.raises(InvalidValueError):
            plan.change_preferences(StudyPreferences(210, frozenset()), NOW, max_in_progress=4)

    def test_outcome_progress_at_max_level_has_no_next_level(self, plan: StudyPlan) -> None:
        content = add(plan, "A")
        master(plan, content)
        plan.start_session(content.id, NOW)
        outcome = plan.finish_session(NOTES, NOW + timedelta(minutes=30), RecallRating.GOOD)
        assert outcome.level is MasteryLevel.ADVANCED
        assert outcome.next_level is None
        assert outcome.points_for_next_level is None
        assert outcome.challenges_for_next_level is None
