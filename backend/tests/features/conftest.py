"""Step definitions compartilhados.

O BDD exercita os CASOS DE USO, não o HTTP (ADR-0008): repositório em memória e
`FakeClock`, então cada cenário roda em milissegundos.
"""

import asyncio
import uuid
from collections.abc import Coroutine, Iterator
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from pytest_bdd import given, parsers, then, when
from tests.features.identity_world import admin  # noqa: F401  (fixture dos cenários de identidade)

from developer_myself.curriculum.domain.unlock import CatalogUnlockPolicy
from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.application.history import RecordSessionHistory
from developer_myself.learning.adapters.memory.notebook_repository import (
    InMemoryNotebookRepository,
)
from developer_myself.learning.adapters.memory.repository import InMemoryStudyPlanRepository
from developer_myself.learning.application.use_cases import (
    AnswerInput,
    LearningUseCases,
    NotesInput,
)
from developer_myself.learning.domain.content import Content
from developer_myself.learning.domain.errors import (
    ChallengeAlreadySolvedError,
    ContentHasProgressError,
    ContentLockedError,
    DomainError,
    DuplicateContentError,
    InvalidTransitionError,
    InvalidValueError,
    MasteryNotReachedError,
    RecallRatingRequiredError,
    SessionAlreadyActiveError,
)
from developer_myself.learning.domain.events import StudySessionAbandoned, StudySessionFinished
from developer_myself.learning.domain.study_plan import SessionOutcome, StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentStatus,
    LearnerId,
    MasteryLevel,
    RecallRating,
    SessionKind,
)
from developer_myself.review_questions import RuleQuestionPicker
from developer_myself.shared.clock import FakeClock

GOOD_NOTES = NotesInput(
    studied="Capítulo sobre funções pequenas e nomes significativos",
    understood="Funções devem fazer uma coisa só e ter um nível de abstração",
    to_review="Diferença entre comando e consulta (CQS) e efeitos colaterais",
)
SHORT_NOTES = NotesInput(studied="cap 3", understood="funções", to_review="cqs")
NO_NOTES = NotesInput(studied="", understood="", to_review="")

LEVELS = {
    "Iniciante": MasteryLevel.BEGINNER,
    "Intermediário": MasteryLevel.INTERMEDIATE,
    "Avançado": MasteryLevel.ADVANCED,
}
STATUSES = {
    "em andamento": ContentStatus.IN_PROGRESS,
    "bloqueado": ContentStatus.LOCKED,
    "consolidado": ContentStatus.CONSOLIDATED,
    "concluído": ContentStatus.FINISHED,
}


@dataclass
class World:
    runner: asyncio.Runner
    timezone: str = "America/Sao_Paulo"
    repository: InMemoryStudyPlanRepository = field(default_factory=InMemoryStudyPlanRepository)
    clock: FakeClock = field(default_factory=FakeClock)
    learner_id: uuid.UUID = field(default_factory=uuid.uuid7)
    outcome: SessionOutcome | None = None
    error: DomainError | None = None
    last_challenge_id: uuid.UUID | None = None
    session_kind: SessionKind | None = None
    history: InMemorySessionHistoryStore = field(default_factory=InMemorySessionHistoryStore)
    notebooks: InMemoryNotebookRepository = field(default_factory=InMemoryNotebookRepository)
    removed_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    _uc: LearningUseCases | None = None

    def __post_init__(self) -> None:
        self.clock.set(self.local_moment(time(8, 0)))
        # Despacho em processo: os eventos alimentam o histórico (como o consumer faria).
        self.repository.subscribers.append(RecordSessionHistory(self.history))

    # ----------------------------------------------------------- infraestrutura
    @property
    def uc(self) -> LearningUseCases:
        if self._uc is None:
            self._uc = LearningUseCases.build(
                self.repository,
                self.clock,
                CatalogUnlockPolicy(),
                notebooks=self.notebooks,
                question_picker=RuleQuestionPicker(),
            )
        return self._uc

    def run[T](self, coro: Coroutine[Any, Any, T]) -> T:
        return self.runner.run(coro)

    def local_moment(self, at: time, days: int = 0) -> datetime:
        tz = ZoneInfo(self.timezone)
        today = self.clock.now().astimezone(tz).date() + timedelta(days=days)
        return datetime.combine(today, at, tzinfo=tz)

    # ----------------------------------------------------------- consultas
    def plan(self) -> StudyPlan:
        plan = self.run(self.repository.get(LearnerId(self.learner_id)))
        assert plan is not None
        return plan

    def content(self, title: str) -> Content:
        found = self.plan().find_by_title(title)
        assert found is not None, f"{title!r} não existe na trilha"
        return found

    # ----------------------------------------------------------- comandos
    def ensure_plan(self) -> None:
        self.run(self.uc.create_plan(self.learner_id, self.timezone))

    def add(self, title: str) -> Content:
        self.ensure_plan()
        return self.run(self.uc.add_content(self.learner_id, title, "BOOK"))

    def ensure_content(self, title: str) -> Content:
        self.ensure_plan()
        return self.plan().find_by_title(title) or self.add(title)

    def session(
        self, title: str, minutes: float, notes: NotesInput = GOOD_NOTES, rating: int = 3
    ) -> None:
        """Revisões recebem a autoavaliação (padrão: 3, "Lembrei bem")."""
        content = self.content(title)
        self.session_kind = self.run(self.uc.start_session(self.learner_id, content.id.value))
        self.clock.advance(minutes=minutes)
        recall = rating if self.session_kind is SessionKind.REVIEW else None
        self.outcome = self.run(
            self.uc.finish_session(self.learner_id, notes, recall, self.answers("RECALLED"))
        )

    def answers(self, grade: str) -> list[AnswerInput]:
        """Responde e corrige o teste de memória da sessão ativa (vazio se não houver)."""
        session = self.plan().active_session
        questions = session.questions if session is not None else ()
        return [AnswerInput(q.id, "minha resposta", grade) for q in questions]

    def earn_points(self, title: str, amount: int) -> None:
        for _ in range(amount):
            self.review_first_if_needed(title)
            self.session(title, 25)
            assert self.outcome is not None
            assert self.outcome.awarded, self.outcome.reason

    def review_first_if_needed(self, title: str) -> None:
        """Para pontuar estudando, é preciso ter revisado algo hoje (regra do ADR-0002)."""
        plan = self.plan()
        target = self.content(title)
        if target.status is not ContentStatus.IN_PROGRESS or plan.reviewed_today(self.clock.now()):
            return
        reviewable = next((c for c in plan.contents if c.is_reviewable), None)
        if reviewable is not None:
            self.session(reviewable.title.value, 25)

    def solve_challenges(self, title: str, amount: int, level: MasteryLevel) -> None:
        content = self.content(title)
        for i in range(amount):
            challenge = self.run(
                self.uc.add_challenge(
                    self.learner_id, content.id.value, f"Desafio {i + 1}", level.value
                )
            )
            self.last_challenge_id = challenge.id.value
            self.run(
                self.uc.solve_challenge(
                    self.learner_id,
                    content.id.value,
                    challenge.id.value,
                    "https://github.com/eu/solucao",
                )
            )

    def consolidate(self, title: str) -> None:
        self.add(title)
        self.earn_points(title, 10)
        self.solve_challenges(title, 3, MasteryLevel.INTERMEDIATE)
        assert self.content(title).status is ContentStatus.CONSOLIDATED
        # "Está consolidado" é um estado do passado: o cenário continua na manhã seguinte.
        self.clock.set(self.local_moment(time(8, 0), days=1))

    def attempt(self, coro: Coroutine[Any, Any, object]) -> None:
        try:
            self.run(coro)
        except DomainError as exc:
            self.error = exc


@pytest.fixture
def world() -> Iterator[World]:
    with asyncio.Runner() as runner:
        yield World(runner=runner)


# ================================================================== Dado
@given(parsers.parse('que meu fuso horário é "{tz}"'))
def given_timezone(world: World, tz: str) -> None:
    world.timezone = tz


@given(parsers.parse('que "{title}" está em andamento'))
def given_in_progress(world: World, title: str) -> None:
    world.add(title)
    assert world.content(title).status is ContentStatus.IN_PROGRESS


@given(parsers.parse('que "{title}" está em andamento com {points:d} pontos'))
def given_in_progress_with_points(world: World, title: str, points: int) -> None:
    given_in_progress(world, title)
    world.earn_points(title, points)


@given(parsers.parse('que "{title}" está consolidado'))
def given_consolidated(world: World, title: str) -> None:
    world.consolidate(title)


@given(parsers.parse('que "{title}" está consolidado com {points:d} pontos'))
def given_consolidated_with_points(world: World, title: str, points: int) -> None:
    world.consolidate(title)
    world.earn_points(title, points - world.content(title).points.value)


@given(parsers.parse('que "{title}" está bloqueado'))
def given_locked(world: World, title: str) -> None:
    world.add(title)
    assert world.content(title).status is ContentStatus.LOCKED


@given(parsers.re(r'que resolvi (?P<amount>\d+) desafios de (?P<level>\w+) em "(?P<title>[^"]+)"'))
def given_solved_challenges(world: World, amount: str, level: str, title: str) -> None:
    world.solve_challenges(title, int(amount), LEVELS[level])


@given(parsers.parse('que cadastrei um desafio de {level} em "{title}"'))
def given_challenge(world: World, level: str, title: str) -> None:
    content = world.content(title)
    challenge = world.run(
        world.uc.add_challenge(
            world.learner_id, content.id.value, "Refatorar um módulo legado", LEVELS[level].value
        )
    )
    world.last_challenge_id = challenge.id.value


@given(parsers.parse('que revisei "{title}" ontem'))
def given_reviewed_yesterday(world: World, title: str) -> None:
    world.session(title, 25)
    assert world.session_kind is SessionKind.REVIEW
    world.clock.set(world.local_moment(time(8, 0), days=1))


@given(parsers.parse("que são {hour:d}:{minute:d} no meu horário local"))
def given_local_time(world: World, hour: int, minute: int) -> None:
    world.clock.set(world.local_moment(time(hour, minute)))


@given(parsers.parse('que iniciei uma sessão em "{title}"'))
def given_started_session(world: World, title: str) -> None:
    content = world.ensure_content(title)
    world.run(world.uc.start_session(world.learner_id, content.id.value))


# ================================================================== Quando
@when(parsers.parse('eu estudo "{title}" por {minutes:d} minutos com anotações'))
@when(parsers.parse('eu reviso "{title}" por {minutes:d} minutos com anotações'))
def when_study(world: World, title: str, minutes: int) -> None:
    world.session(title, minutes)


@when(parsers.parse('eu estudo "{title}" por {minutes:d} minutos sem anotações'))
def when_study_without_notes(world: World, title: str, minutes: int) -> None:
    world.session(title, minutes, NO_NOTES)


@when(parsers.parse('eu estudo "{title}" por {minutes:d} minutos com anotações curtas'))
def when_study_short_notes(world: World, title: str, minutes: int) -> None:
    world.session(title, minutes, SHORT_NOTES)


@when(parsers.parse('eu ganho 1 ponto em "{title}"'))
def when_earn_point(world: World, title: str) -> None:
    world.earn_points(title, 1)


@when(parsers.parse('eu adiciono "{title}"'))
def when_add(world: World, title: str) -> None:
    world.add(title)


@when(parsers.re(r'eu resolvo o \dº desafio de (?P<level>\w+) em "(?P<title>[^"]+)" com evidência'))
def when_solve_next(world: World, level: str, title: str) -> None:
    world.solve_challenges(title, 1, LEVELS[level])


@when(parsers.parse('eu tento iniciar uma sessão em "{title}"'))
def when_try_start(world: World, title: str) -> None:
    world.attempt(world.uc.start_session(world.learner_id, world.content(title).id.value))


@when(parsers.parse('eu inicio uma sessão em "{title}" {hours:d} horas depois'))
def when_start_later(world: World, title: str, hours: int) -> None:
    world.clock.advance(hours=hours)
    when_start(world, title)


@when(parsers.parse('eu inicio uma sessão em "{title}"'))
def when_start(world: World, title: str) -> None:
    world.session_kind = world.run(
        world.uc.start_session(world.learner_id, world.content(title).id.value)
    )


@when(
    parsers.parse("eu finalizo a sessão {hours:d} horas e {minutes:d} minuto depois com anotações")
)
def when_finish_late(world: World, hours: int, minutes: int) -> None:
    world.clock.advance(hours=hours, minutes=minutes)
    world.outcome = world.run(world.uc.finish_session(world.learner_id, GOOD_NOTES))


@when("eu cancelo a sessão")
def when_cancel(world: World) -> None:
    world.run(world.uc.cancel_session(world.learner_id))


@given(parsers.parse('que concluí "{title}"'))
@when(parsers.parse('eu concluo "{title}"'))
def when_finish_content(world: World, title: str) -> None:
    world.run(world.uc.finish_content(world.learner_id, world.content(title).id.value))


@when(parsers.parse('eu tento concluir "{title}"'))
def when_try_finish_content(world: World, title: str) -> None:
    world.attempt(world.uc.finish_content(world.learner_id, world.content(title).id.value))


@then(parsers.parse('a conclusão é recusada porque "{title}" ainda não chegou a Avançado'))
def then_finish_refused(world: World, title: str) -> None:
    assert isinstance(world.error, MasteryNotReachedError), world.error
    assert f"{title} só pode ser concluído no nível Avançado" in str(world.error)


def _solve_last(world: World, evidence: str) -> None:
    assert world.last_challenge_id is not None
    content = next(c for c in world.plan().contents if c.challenges)
    world.attempt(
        world.uc.solve_challenge(
            world.learner_id, content.id.value, world.last_challenge_id, evidence
        )
    )


@when("eu tento resolver o desafio sem evidência")
def when_solve_without_evidence(world: World) -> None:
    _solve_last(world, "   ")


@when("eu tento resolver o mesmo desafio de novo")
def when_solve_again(world: World) -> None:
    _solve_last(world, "outra evidência")


# ================================================================== Então
@then(parsers.re(r'"(?P<title>[^"]+)" tem (?P<points>\d+) pontos?'))
def then_points(world: World, title: str, points: str) -> None:
    assert world.content(title).points.value == int(points)


@then(parsers.parse('o motivo é "{reason}"'))
def then_reason(world: World, reason: str) -> None:
    assert world.outcome is not None
    assert world.outcome.reason is not None
    assert world.outcome.reason.value == reason


@then(
    parsers.re(
        r'"(?P<title>[^"]+)" (?:fica|continua) '
        r"(?P<status>em andamento|bloqueado|consolidado|concluído)$"
    )
)
def then_status(world: World, title: str, status: str) -> None:
    assert world.content(title).status is STATUSES[status]


@then(
    parsers.re(r'"(?P<title>[^"]+)" (?:fica|continua) (?P<level>Iniciante|Intermediário|Avançado)$')
)
def then_level(world: World, title: str, level: str) -> None:
    plan = world.plan()
    assert plan.level_of(world.content(title)) is LEVELS[level]


@then(parsers.parse('sou avisado de que preciso concluir "{current}" ou chegar a Intermediário'))
def then_warned(world: World, current: str) -> None:
    plan = world.plan()
    locked = plan.queue[-1]
    assert f"conclua {current} ou chegue a Intermediário" in plan.lock_reason(locked)


@then("a sessão é recusada porque o conteúdo está bloqueado")
def then_refused_locked(world: World) -> None:
    assert isinstance(world.error, ContentLockedError)


@then("a sessão é recusada porque já existe uma sessão ativa")
def then_refused_active(world: World) -> None:
    assert isinstance(world.error, SessionAlreadyActiveError)


@then("a sessão anterior foi abandonada")
def then_abandoned(world: World) -> None:
    assert any(isinstance(e, StudySessionAbandoned) for e in world.repository.outbox)


@then(parsers.parse('existe uma sessão ativa em "{title}"'))
def then_active_on(world: World, title: str) -> None:
    active = world.plan().active_session
    assert active is not None
    assert active.content_id == world.content(title).id


@then("não existe sessão ativa")
def then_no_active(world: World) -> None:
    assert world.plan().active_session is None


@then("a sessão é de revisão")
def then_review_kind(world: World) -> None:
    assert world.session_kind is SessionKind.REVIEW


@then("a resolução é recusada")
def then_solve_refused(world: World) -> None:
    assert isinstance(world.error, InvalidValueError | ChallengeAlreadySolvedError)


@then("o desafio continua pendente")
def then_challenge_pending(world: World) -> None:
    content = next(c for c in world.plan().contents if c.challenges)
    assert not any(c.is_solved for c in content.challenges)


@given(parsers.parse('que revisei "{title}" hoje'))
def given_reviewed_today(world: World, title: str) -> None:
    world.session(title, 25)


@given(parsers.parse('que se passaram {days:d} dias desde a última atividade em "{title}"'))
def given_idle_since_last_activity(world: World, days: int, title: str) -> None:
    content = world.content(title)
    moments = [content.last_session_at, *(c.solved_at for c in content.challenges)]
    world.clock.set(max(m for m in moments if m is not None) + timedelta(days=days))


@given(parsers.parse("que se passaram {days:d} dias"))
def given_days_passed(world: World, days: int) -> None:
    world.clock.advance(days=days)


# ================================================================== autoavaliação
RATINGS = {"Esqueci": 1, "Difícil": 2, "Bem": 3, "Fácil": 4}


@when(parsers.parse('eu reviso "{title}" por {minutes:d} minutos lembrando "{rating}"'))
def when_review_with_rating(world: World, title: str, minutes: int, rating: str) -> None:
    world.session(title, minutes, rating=RATINGS[rating])
    assert world.session_kind is SessionKind.REVIEW


@when("eu tento finalizar a revisão sem dizer quanto lembrava")
def when_finish_review_without_rating(world: World) -> None:
    world.clock.advance(minutes=25)
    world.attempt(world.uc.finish_session(world.learner_id, GOOD_NOTES, None))


@then("a finalização é recusada pedindo a autoavaliação")
def then_rating_required(world: World) -> None:
    assert isinstance(world.error, RecallRatingRequiredError)


def last_finished(world: World) -> StudySessionFinished:
    return next(e for e in reversed(world.repository.outbox) if isinstance(e, StudySessionFinished))


@then(
    parsers.parse("o histórico registra a nota {rating:d} com {days:d} dias desde o último contato")
)
def then_label_recorded(world: World, rating: int, days: int) -> None:
    event = last_finished(world)
    assert event.recall_rating == rating
    assert event.last_contact_days is not None
    assert round(event.last_contact_days) == days
    assert event.points_before >= 10
    assert event.review_count_before == 0


@then(parsers.re(r"a revisão conta como (?P<result>lembrada|esquecida)"))
def then_remembered(world: World, result: str) -> None:
    rating = last_finished(world).recall_rating
    assert rating is not None
    assert RecallRating(rating).remembered is (result == "lembrada")


# ================================================================== organizar a trilha
@when(parsers.parse('eu removo "{title}"'))
def when_remove(world: World, title: str) -> None:
    content_id = world.content(title).id.value
    world.run(world.uc.remove_content(world.learner_id, content_id))
    world.removed_ids[title] = content_id


@when(parsers.parse('eu tento remover "{title}"'))
def when_try_remove(world: World, title: str) -> None:
    world.attempt(world.uc.remove_content(world.learner_id, world.content(title).id.value))


@when(parsers.parse('eu renomeio "{old}" para "{new}"'))
def when_rename(world: World, old: str, new: str) -> None:
    world.run(world.uc.rename_content(world.learner_id, world.content(old).id.value, new))


@when(parsers.parse('eu tento renomear "{old}" para "{new}"'))
def when_try_rename(world: World, old: str, new: str) -> None:
    world.attempt(world.uc.rename_content(world.learner_id, world.content(old).id.value, new))


@then(parsers.parse('"{title}" não está mais na trilha'))
def then_removed(world: World, title: str) -> None:
    assert world.plan().find_by_title(title) is None


@then(parsers.parse('a remoção é recusada porque "{title}" já tem progresso'))
def then_remove_refused(world: World, title: str) -> None:
    assert isinstance(world.error, ContentHasProgressError), world.error
    assert title in str(world.error)


@then("a renomeação é recusada por título repetido")
def then_rename_refused(world: World) -> None:
    assert isinstance(world.error, DuplicateContentError), world.error


@when(parsers.parse('eu resolvo {amount:d} desafios de {level} em "{title}"'))
def when_solve_many(world: World, amount: int, level: str, title: str) -> None:
    world.solve_challenges(title, amount, LEVELS[level])


@then(parsers.parse('sou avisado de que "{title}" espera uma vaga entre os 3 em andamento'))
def then_waits_for_slot(world: World, title: str) -> None:
    plan = world.plan()
    assert "já há 3 conteúdos em andamento" in plan.lock_reason(world.content(title))


# ================================================================== reordenar a fila
def _ids(world: World, titles: str) -> list[uuid.UUID]:
    return [world.content(t.strip()).id.value for t in titles.split(",")]


@given(parsers.parse('que eu reordenei a fila para "{titles}"'))
@when(parsers.parse('eu reordeno a fila para "{titles}"'))
def when_reorder(world: World, titles: str) -> None:
    world.run(world.uc.reorder_queue(world.learner_id, _ids(world, titles)))


@when(parsers.parse('eu tento reordenar a fila para "{titles}"'))
def when_try_reorder(world: World, titles: str) -> None:
    world.attempt(world.uc.reorder_queue(world.learner_id, _ids(world, titles)))


@then(parsers.parse('a fila fica "{titles}"'))
def then_queue(world: World, titles: str) -> None:
    assert [c.title.value for c in world.plan().queue] == [t.strip() for t in titles.split(",")]


@then("a reordenação é recusada")
def then_reorder_refused(world: World) -> None:
    assert isinstance(world.error, InvalidTransitionError), world.error
