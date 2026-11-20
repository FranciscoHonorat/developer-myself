"""Casos de uso do contexto `learning`. Cada um é um port de entrada (ADR-0003).

Padrão: carregar o agregado → chamar `clock.now()` → executar o comando → salvar.
"""

import uuid
from dataclasses import dataclass

from developer_myself.learning.application.notebooks import NotebookUseCases
from developer_myself.learning.application.questions import QuestionPicker
from developer_myself.learning.domain.content import Challenge, Content
from developer_myself.learning.domain.errors import (
    DomainError,
    InvalidValueError,
    StudyPlanNotFoundError,
)
from developer_myself.learning.domain.policies import UnlockPolicy
from developer_myself.learning.domain.repository import NotebookRepository, StudyPlanRepository
from developer_myself.learning.domain.study_plan import SessionOutcome, StudyPlan
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    ContentKind,
    Evidence,
    LearnerId,
    MasteryLevel,
    Notes,
    RecallAnswer,
    RecallGrade,
    RecallRating,
    SessionKind,
    StudyPreferences,
    Timezone,
    Title,
)
from developer_myself.shared.clock import Clock


@dataclass(slots=True)
class _UseCase:
    repository: StudyPlanRepository
    clock: Clock
    unlock_policy: UnlockPolicy | None = None

    def _with_policy(self, plan: StudyPlan) -> StudyPlan:
        if self.unlock_policy is not None:
            plan.unlock_policy = self.unlock_policy
        return plan

    async def _load(self, learner_id: uuid.UUID) -> StudyPlan:
        plan = await self.repository.get(LearnerId(learner_id))
        if plan is None:
            raise StudyPlanNotFoundError("Trilha de estudo não encontrada.")
        return self._with_policy(plan)


@dataclass(slots=True)
class CreateStudyPlan(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, timezone: str) -> StudyPlan:
        existing = await self.repository.get(LearnerId(learner_id))
        if existing is not None:
            return self._with_policy(existing)
        plan = self._with_policy(StudyPlan.create(LearnerId(learner_id), Timezone(timezone)))
        await self.repository.save(plan)
        return plan


@dataclass(slots=True)
class GetStudyPlan(_UseCase):
    async def __call__(self, learner_id: uuid.UUID) -> StudyPlan:
        return await self._load(learner_id)


@dataclass(slots=True)
class ChangeTimezone(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, timezone: str) -> None:
        plan = await self._load(learner_id)
        plan.change_timezone(Timezone(timezone))
        await self.repository.save(plan)


@dataclass(slots=True)
class AddContent(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, title: str, kind: str) -> Content:
        plan = await self._load(learner_id)
        content = plan.add_content(
            ContentId.new(), Title(title), ContentKind(kind), self.clock.now()
        )
        await self.repository.save(plan)
        return content


@dataclass(slots=True)
class StartSession(_UseCase):
    question_picker: QuestionPicker | None = None

    async def __call__(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> SessionKind:
        plan = await self._load(learner_id)
        now = self.clock.now()
        try:
            content = plan.content(ContentId(content_id))
            questions = (
                self.question_picker.pick(plan, content, now)
                if self.question_picker is not None and content.session_kind is SessionKind.REVIEW
                else ()
            )
            kind = plan.start_session(content.id, now, questions)
        except DomainError:
            # Uma sessão expirada pode ter sido abandonada antes do erro: persistir isso.
            if plan.pending_events:
                await self.repository.save(plan)
            raise
        await self.repository.save(plan)
        return kind


@dataclass(frozen=True, slots=True)
class NotesInput:
    studied: str
    understood: str
    to_review: str


@dataclass(frozen=True, slots=True)
class AnswerInput:
    question_id: uuid.UUID
    answer: str
    grade: str
    useful: bool | None = None


def _answer(item: AnswerInput) -> RecallAnswer:
    try:
        grade = RecallGrade(item.grade)
    except ValueError as exc:
        raise InvalidValueError("Corrija com Errei, Parcial ou Acertei.") from exc
    return RecallAnswer(item.question_id, item.answer, grade, item.useful)


def _rating(value: int | None) -> RecallRating | None:
    if value is None:
        return None
    try:
        return RecallRating(value)
    except ValueError as exc:
        raise InvalidValueError("A autoavaliação vai de 1 (Esqueci) a 4 (Fácil).") from exc


@dataclass(slots=True)
class FinishSession(_UseCase):
    async def __call__(
        self,
        learner_id: uuid.UUID,
        notes: NotesInput,
        recall_rating: int | None = None,
        answers: list[AnswerInput] | None = None,
    ) -> SessionOutcome:
        plan = await self._load(learner_id)
        rating = _rating(recall_rating)
        outcome = plan.finish_session(
            Notes(notes.studied, notes.understood, notes.to_review),
            self.clock.now(),
            rating,
            tuple(_answer(a) for a in answers or ()),
        )
        await self.repository.save(plan)
        return outcome


@dataclass(slots=True)
class CancelSession(_UseCase):
    async def __call__(self, learner_id: uuid.UUID) -> None:
        plan = await self._load(learner_id)
        plan.cancel_session(self.clock.now())
        await self.repository.save(plan)


@dataclass(slots=True)
class AddChallenge(_UseCase):
    async def __call__(
        self, learner_id: uuid.UUID, content_id: uuid.UUID, description: str, target_level: str
    ) -> Challenge:
        plan = await self._load(learner_id)
        challenge = plan.add_challenge(
            ContentId(content_id),
            ChallengeId.new(),
            description,
            MasteryLevel(target_level),
            self.clock.now(),
        )
        await self.repository.save(plan)
        return challenge


@dataclass(slots=True)
class SolveChallenge(_UseCase):
    async def __call__(
        self,
        learner_id: uuid.UUID,
        content_id: uuid.UUID,
        challenge_id: uuid.UUID,
        evidence: str,
    ) -> MasteryLevel:
        plan = await self._load(learner_id)
        level = plan.solve_challenge(
            ContentId(content_id), ChallengeId(challenge_id), Evidence(evidence), self.clock.now()
        )
        await self.repository.save(plan)
        return level


@dataclass(slots=True)
class FinishContent(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> ContentId | None:
        plan = await self._load(learner_id)
        unlocked = plan.finish_content(ContentId(content_id), self.clock.now())
        await self.repository.save(plan)
        return unlocked


@dataclass(slots=True)
class RemoveContent(_UseCase):
    notebooks: NotebookRepository | None = None

    async def __call__(self, learner_id: uuid.UUID, content_id: uuid.UUID) -> ContentId | None:
        plan = await self._load(learner_id)
        unlocked = plan.remove_content(ContentId(content_id), self.clock.now())
        await self.repository.save(plan)
        if self.notebooks is not None:
            await self.notebooks.delete(LearnerId(learner_id), ContentId(content_id))
        return unlocked


@dataclass(slots=True)
class RenameContent(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, content_id: uuid.UUID, title: str) -> None:
        plan = await self._load(learner_id)
        plan.rename_content(ContentId(content_id), Title(title), self.clock.now())
        await self.repository.save(plan)


@dataclass(slots=True)
class ChangePreferences(_UseCase):
    async def __call__(
        self, learner_id: uuid.UUID, minutes_per_day: int, rest_days: list[int]
    ) -> StudyPreferences:
        plan = await self._load(learner_id)
        preferences = StudyPreferences(minutes_per_day, frozenset(rest_days))
        plan.change_preferences(preferences, self.clock.now())
        await self.repository.save(plan)
        return preferences


@dataclass(slots=True)
class ReorderQueue(_UseCase):
    async def __call__(self, learner_id: uuid.UUID, content_ids: list[uuid.UUID]) -> None:
        plan = await self._load(learner_id)
        plan.reorder_queue([ContentId(i) for i in content_ids], self.clock.now())
        await self.repository.save(plan)


@dataclass(slots=True)
class RefreshQueue(_UseCase):
    """Ocupa as vagas livres da trilha (ex.: depois que passou a permitir 3 em paralelo)."""

    async def __call__(self, learner_id: uuid.UUID) -> list[ContentId]:
        plan = await self._load(learner_id)
        unlocked = plan.refresh_queue(self.clock.now())
        if unlocked:
            await self.repository.save(plan)
        return unlocked


@dataclass(slots=True)
class LearningUseCases:
    """Agrupa os casos de uso montados pelo composition root."""

    create_plan: CreateStudyPlan
    get_plan: GetStudyPlan
    change_timezone: ChangeTimezone
    add_content: AddContent
    start_session: StartSession
    finish_session: FinishSession
    cancel_session: CancelSession
    add_challenge: AddChallenge
    solve_challenge: SolveChallenge
    finish_content: FinishContent
    remove_content: RemoveContent
    rename_content: RenameContent
    refresh_queue: RefreshQueue
    reorder_queue: ReorderQueue
    change_preferences: ChangePreferences
    notebooks: NotebookUseCases

    @classmethod
    def build(
        cls,
        repository: StudyPlanRepository,
        clock: Clock,
        unlock_policy: UnlockPolicy | None = None,
        *,
        notebooks: NotebookRepository,
        question_picker: QuestionPicker | None = None,
    ) -> LearningUseCases:
        args = (repository, clock, unlock_policy)
        return cls(
            create_plan=CreateStudyPlan(*args),
            get_plan=GetStudyPlan(*args),
            change_timezone=ChangeTimezone(*args),
            add_content=AddContent(*args),
            start_session=StartSession(*args, question_picker=question_picker),
            finish_session=FinishSession(*args),
            cancel_session=CancelSession(*args),
            add_challenge=AddChallenge(*args),
            solve_challenge=SolveChallenge(*args),
            finish_content=FinishContent(*args),
            remove_content=RemoveContent(*args, notebooks=notebooks),
            rename_content=RenameContent(*args),
            refresh_queue=RefreshQueue(*args),
            reorder_queue=ReorderQueue(*args),
            change_preferences=ChangePreferences(*args),
            notebooks=NotebookUseCases(repository, notebooks, clock),
        )
