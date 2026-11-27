"""Adapter HTTP fino: traduz HTTP ⇄ casos de uso. Nenhuma regra de negócio aqui."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from developer_myself.learning.adapters.http.schemas import (
    AddChallengeIn,
    AddContentIn,
    ChallengeOut,
    ContentOut,
    FinishSessionIn,
    LevelOut,
    NotebookIn,
    NotebookOut,
    NotebookSummaryOut,
    OutcomeOut,
    PlanOut,
    PreferencesIn,
    PurposeIn,
    RenameContentIn,
    ReorderQueueIn,
    SolveChallengeIn,
    StartSessionIn,
    StartSessionOut,
    TimezoneIn,
    UnlockedOut,
)
from developer_myself.learning.application.use_cases import (
    AnswerInput,
    FutureQuestionInput,
    LearningUseCases,
    NotesInput,
)
from developer_myself.shared.adapters.http import LearnerIdDep


def get_learning(request: Request) -> LearningUseCases:
    uc: LearningUseCases = request.app.state.container.learning
    return uc


UseCases = Annotated[LearningUseCases, Depends(get_learning)]

router = APIRouter(prefix="/api", tags=["learning"])


@router.get("/plan")
async def get_plan(request: Request, learner_id: LearnerIdDep, uc: UseCases) -> PlanOut:
    plan = await uc.get_plan(learner_id)
    return PlanOut.of(plan, request.app.state.container.clock.now())


@router.put("/plan/timezone", status_code=status.HTTP_204_NO_CONTENT)
async def change_timezone(body: TimezoneIn, learner_id: LearnerIdDep, uc: UseCases) -> None:
    await uc.change_timezone(learner_id, body.timezone)


@router.put("/plan/purpose", status_code=status.HTTP_204_NO_CONTENT)
async def change_purpose(body: PurposeIn, learner_id: LearnerIdDep, uc: UseCases) -> None:
    await uc.change_purpose(learner_id, body.purpose)


@router.post("/contents", status_code=status.HTTP_201_CREATED)
async def add_content(body: AddContentIn, learner_id: LearnerIdDep, uc: UseCases) -> ContentOut:
    content = await uc.add_content(learner_id, body.title, body.kind.value, body.purpose)
    plan = await uc.get_plan(learner_id)
    return ContentOut.of(plan, plan.content(content.id))


@router.put("/contents/{content_id}/purpose", status_code=status.HTTP_204_NO_CONTENT)
async def change_content_purpose(
    content_id: uuid.UUID, body: PurposeIn, learner_id: LearnerIdDep, uc: UseCases
) -> None:
    await uc.change_content_purpose(learner_id, content_id, body.purpose)


@router.post("/contents/{content_id}/finish")
async def finish_content(
    content_id: uuid.UUID, learner_id: LearnerIdDep, uc: UseCases
) -> UnlockedOut:
    unlocked = await uc.finish_content(learner_id, content_id)
    return UnlockedOut(unlocked_content_id=unlocked.value if unlocked else None)


@router.patch("/contents/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def rename_content(
    content_id: uuid.UUID, body: RenameContentIn, learner_id: LearnerIdDep, uc: UseCases
) -> None:
    await uc.rename_content(learner_id, content_id, body.title)


@router.delete("/contents/{content_id}")
async def remove_content(
    content_id: uuid.UUID, learner_id: LearnerIdDep, uc: UseCases
) -> UnlockedOut:
    unlocked = await uc.remove_content(learner_id, content_id)
    return UnlockedOut(unlocked_content_id=unlocked.value if unlocked else None)


@router.put("/plan/preferences", status_code=status.HTTP_204_NO_CONTENT)
async def change_preferences(body: PreferencesIn, learner_id: LearnerIdDep, uc: UseCases) -> None:
    await uc.change_preferences(
        learner_id, body.minutes_per_day, body.rest_days, body.max_in_progress
    )


@router.put("/queue", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_queue(body: ReorderQueueIn, learner_id: LearnerIdDep, uc: UseCases) -> None:
    """Os conteúdos dados vão para a frente da fila, na ordem enviada."""
    await uc.reorder_queue(learner_id, body.content_ids)


@router.post("/contents/{content_id}/challenges", status_code=status.HTTP_201_CREATED)
async def add_challenge(
    content_id: uuid.UUID, body: AddChallengeIn, learner_id: LearnerIdDep, uc: UseCases
) -> ChallengeOut:
    challenge = await uc.add_challenge(
        learner_id, content_id, body.description, body.target_level.value
    )
    return ChallengeOut.of(challenge)


@router.post("/contents/{content_id}/challenges/{challenge_id}/solve")
async def solve_challenge(
    content_id: uuid.UUID,
    challenge_id: uuid.UUID,
    body: SolveChallengeIn,
    learner_id: LearnerIdDep,
    uc: UseCases,
) -> LevelOut:
    level = await uc.solve_challenge(learner_id, content_id, challenge_id, body.evidence)
    return LevelOut(level=level)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(
    body: StartSessionIn, learner_id: LearnerIdDep, uc: UseCases
) -> StartSessionOut:
    kind = await uc.start_session(learner_id, body.content_id)
    return StartSessionOut(kind=kind.value)


@router.post("/sessions/current/finish")
async def finish_session(
    body: FinishSessionIn, learner_id: LearnerIdDep, uc: UseCases
) -> OutcomeOut:
    outcome = await uc.finish_session(
        learner_id,
        NotesInput(body.studied, body.understood, body.to_review),
        body.recall_rating,
        [AnswerInput(a.question_id, a.answer, a.grade, a.useful) for a in body.answers],
        (
            FutureQuestionInput(body.future_question.text, body.future_question.answer)
            if body.future_question is not None
            else None
        ),
    )
    return OutcomeOut.of(outcome)


@router.post("/sessions/current/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(learner_id: LearnerIdDep, uc: UseCases) -> None:
    await uc.cancel_session(learner_id)


# --------------------------------------------------------------------------- caderno
@router.get("/contents/{content_id}/notebook")
async def get_notebook(
    content_id: uuid.UUID, learner_id: LearnerIdDep, uc: UseCases
) -> NotebookOut:
    return NotebookOut.of(await uc.notebooks.get(learner_id, content_id))


@router.put("/contents/{content_id}/notebook")
async def save_notebook(
    content_id: uuid.UUID, body: NotebookIn, learner_id: LearnerIdDep, uc: UseCases
) -> NotebookOut:
    notebook = await uc.notebooks.save(learner_id, content_id, body.text, body.version)
    return NotebookOut.of(notebook)


@router.get("/notebooks")
async def list_notebooks(learner_id: LearnerIdDep, uc: UseCases) -> list[NotebookSummaryOut]:
    return [NotebookSummaryOut.of(n) for n in await uc.notebooks.list(learner_id)]
