"""DTOs da borda HTTP. Pydantic SÓ aqui (ADR-0004); `StrictStr` recusa `{"$ne": null}`."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from developer_myself.learning.domain.content import Challenge, Content
from developer_myself.learning.domain.notebook import NOTEBOOK_MAX_CHARS, Notebook
from developer_myself.learning.domain.study_plan import SESSION_EXPIRY, SessionOutcome, StudyPlan
from developer_myself.learning.domain.value_objects import (
    ANSWER_MAX_LENGTH,
    LEARNER_ANSWER_MAX_LENGTH,
    MAX_PARALLEL_CONTENTS,
    MIN_PARALLEL_CONTENTS,
    PURPOSE_MAX_LENGTH,
    QUESTION_MAX_LENGTH,
    ContentKind,
    ContentStatus,
    MasteryLevel,
    RecallQuestion,
)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddContentIn(_In):
    title: StrictStr = Field(min_length=1, max_length=200)
    kind: ContentKind = ContentKind.BOOK
    purpose: StrictStr | None = Field(default=None, max_length=PURPOSE_MAX_LENGTH)


class RenameContentIn(_In):
    title: StrictStr = Field(min_length=1, max_length=200)


class PurposeIn(_In):
    purpose: StrictStr | None = Field(default=None, max_length=PURPOSE_MAX_LENGTH)


class PreferencesIn(_In):
    minutes_per_day: int = Field(ge=60, le=480, strict=True)
    rest_days: list[int] = Field(default_factory=list, max_length=6)
    max_in_progress: int | None = Field(
        default=None, ge=MIN_PARALLEL_CONTENTS, le=MAX_PARALLEL_CONTENTS, strict=True
    )


class ReorderQueueIn(_In):
    content_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class StartSessionIn(_In):
    content_id: uuid.UUID


class AnswerIn(_In):
    question_id: uuid.UUID
    answer: StrictStr = Field(default="", max_length=ANSWER_MAX_LENGTH)
    grade: Literal["MISSED", "PARTIAL", "RECALLED"]
    useful: bool | None = None


class FutureQuestionIn(_In):
    text: StrictStr = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)
    answer: StrictStr | None = Field(default=None, max_length=LEARNER_ANSWER_MAX_LENGTH)


class FinishSessionIn(_In):
    studied: StrictStr = Field(default="", max_length=10_000)
    understood: StrictStr = Field(default="", max_length=10_000)
    to_review: StrictStr = Field(default="", max_length=10_000)
    recall_rating: int | None = Field(default=None, ge=1, le=4, strict=True)
    answers: list[AnswerIn] = Field(default_factory=list, max_length=10)
    future_question: FutureQuestionIn | None = None


class FinishWarmupIn(_In):
    answers: list[AnswerIn] = Field(default_factory=list, max_length=10)


class AddChallengeIn(_In):
    description: StrictStr = Field(min_length=1, max_length=2_000)
    target_level: MasteryLevel = MasteryLevel.INTERMEDIATE


class SolveChallengeIn(_In):
    evidence: StrictStr = Field(max_length=10_000)


class NotebookIn(_In):
    text: StrictStr = Field(max_length=NOTEBOOK_MAX_CHARS)
    version: int = Field(ge=0)


class TimezoneIn(_In):
    timezone: StrictStr = Field(min_length=1, max_length=64)


# --------------------------------------------------------------------------- saída


class ChallengeOut(BaseModel):
    id: uuid.UUID
    description: str
    target_level: MasteryLevel
    created_at: datetime
    solved: bool
    solved_at: datetime | None
    evidence: str | None

    @classmethod
    def of(cls, c: Challenge) -> ChallengeOut:
        return cls(
            id=c.id.value,
            description=c.description,
            target_level=c.target_level,
            created_at=c.created_at,
            solved=c.is_solved,
            solved_at=c.solved_at,
            evidence=c.evidence.value if c.evidence else None,
        )


class NextLevelOut(BaseModel):
    level: MasteryLevel
    points_required: int
    challenges_required: int
    challenges_solved: int


class ContentOut(BaseModel):
    id: uuid.UUID
    title: str
    kind: ContentKind
    status: ContentStatus
    points: int
    level: MasteryLevel
    next_level: NextLevelOut | None
    queued_at: datetime
    finished_at: datetime | None
    last_session_at: datetime | None
    queue_position: int | None
    lock_reason: str | None
    challenges: list[ChallengeOut]
    last_to_review: str | None
    purpose: str | None = None
    daily: bool  # hábito diário (ex.: Inglês): em andamento fora das vagas

    @classmethod
    def of(cls, plan: StudyPlan, c: Content) -> ContentOut:
        level = plan.level_of(c)
        queue = plan.queue
        position = queue.index(c) + 1 if c in queue else None
        requirements = plan.mastery_policy.requirements()
        next_level = next(
            (lvl for lvl in sorted(requirements, key=lambda x: x.rank) if lvl.rank > level.rank),
            None,
        )
        nxt = None
        if next_level is not None:
            points_req, challenges_req = requirements[next_level]
            nxt = NextLevelOut(
                level=next_level,
                points_required=points_req,
                challenges_required=challenges_req,
                challenges_solved=sum(1 for lvl in c.solved_challenge_levels if lvl is next_level),
            )
        return cls(
            id=c.id.value,
            title=c.title.value,
            kind=c.kind,
            status=c.status,
            points=c.points.value,
            level=level,
            next_level=nxt,
            queued_at=c.queued_at,
            finished_at=c.finished_at,
            last_session_at=c.last_session_at,
            daily=plan.is_daily(c),
            queue_position=position,
            lock_reason=plan.lock_reason(c) if c.status is ContentStatus.LOCKED else None,
            challenges=[ChallengeOut.of(ch) for ch in c.challenges],
            last_to_review=c.last_to_review,
            purpose=c.purpose.value if c.purpose else None,
        )


class QuestionOut(BaseModel):
    id: uuid.UUID
    text: str
    source: str
    expected_answer: str | None = None

    @classmethod
    def of(cls, q: RecallQuestion) -> QuestionOut:
        return cls(id=q.id, text=q.text, source=q.source.value, expected_answer=q.expected_answer)


class ActiveSessionOut(BaseModel):
    content_id: uuid.UUID
    content_title: str
    content_purpose: str | None = None
    kind: str | None
    started_at: datetime
    expires_at: datetime
    questions: list[QuestionOut]
    last_to_review: str | None


class PreferencesOut(BaseModel):
    minutes_per_day: int
    rest_days: list[int]


class PlanOut(BaseModel):
    timezone: str
    purpose: str | None = None
    preferences: PreferencesOut
    max_in_progress: int
    server_time: datetime
    last_review_on: date | None
    reviewed_today: bool
    needs_review_today: bool
    active_session: ActiveSessionOut | None
    contents: list[ContentOut]

    @classmethod
    def of(cls, plan: StudyPlan, now: datetime) -> PlanOut:
        active = None
        if plan.active_session is not None:
            content = plan.content(plan.active_session.content_id)
            kind = content.session_kind
            active = ActiveSessionOut(
                content_id=content.id.value,
                content_title=content.title.value,
                content_purpose=content.purpose.value if content.purpose else None,
                kind=kind.value if kind else None,
                started_at=plan.active_session.started_at,
                expires_at=plan.active_session.started_at + SESSION_EXPIRY,
                questions=[QuestionOut.of(q) for q in plan.active_session.questions],
                last_to_review=content.last_to_review,
            )
        reviewed = plan.reviewed_today(now)
        return cls(
            timezone=plan.timezone.name,
            purpose=plan.purpose.value if plan.purpose else None,
            preferences=PreferencesOut(
                minutes_per_day=plan.preferences.minutes_per_day,
                rest_days=sorted(plan.preferences.rest_days),
            ),
            max_in_progress=plan.effective_max_in_progress,
            server_time=now,
            last_review_on=plan.last_review_on,
            reviewed_today=reviewed,
            needs_review_today=plan.requires_review(now) and not reviewed,
            active_session=active,
            contents=[ContentOut.of(plan, c) for c in plan.contents],
        )


class StartSessionOut(BaseModel):
    kind: str


class OutcomeOut(BaseModel):
    content_id: uuid.UUID
    kind: str
    duration_seconds: int
    awarded: bool
    reason: str | None
    total_points: int
    level: MasteryLevel
    unlocked_content_id: uuid.UUID | None
    level_before: MasteryLevel
    next_level: MasteryLevel | None
    points_for_next_level: int | None
    challenges_solved: int
    challenges_for_next_level: int | None
    recall_recalled: int
    recall_total: int

    @classmethod
    def of(cls, o: SessionOutcome) -> OutcomeOut:
        return cls(
            content_id=o.content_id.value,
            kind=o.kind.value,
            duration_seconds=o.duration.total_seconds,
            awarded=o.awarded,
            reason=o.reason.value if o.reason else None,
            total_points=o.total_points,
            level=o.level,
            unlocked_content_id=o.unlocked.value if o.unlocked else None,
            level_before=o.level_before,
            next_level=o.next_level,
            points_for_next_level=o.points_for_next_level,
            challenges_solved=o.challenges_solved,
            challenges_for_next_level=o.challenges_for_next_level,
            recall_recalled=o.recall_recalled,
            recall_total=o.recall_total,
        )


class LevelOut(BaseModel):
    level: MasteryLevel


class UnlockedOut(BaseModel):
    unlocked_content_id: uuid.UUID | None


class NotebookOut(BaseModel):
    content_id: uuid.UUID
    text: str
    version: int
    updated_at: datetime | None

    @classmethod
    def of(cls, notebook: Notebook) -> NotebookOut:
        return cls(
            content_id=notebook.content_id.value,
            text=notebook.text,
            version=notebook.version,
            updated_at=notebook.updated_at,
        )


class NotebookSummaryOut(BaseModel):
    content_id: uuid.UUID
    chars: int
    updated_at: datetime | None

    @classmethod
    def of(cls, notebook: Notebook) -> NotebookSummaryOut:
        return cls(
            content_id=notebook.content_id.value,
            chars=notebook.chars,
            updated_at=notebook.updated_at,
        )
