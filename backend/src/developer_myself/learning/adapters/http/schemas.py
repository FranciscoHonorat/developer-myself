"""DTOs da borda HTTP. Pydantic SÓ aqui (ADR-0004); `StrictStr` recusa `{"$ne": null}`."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from developer_myself.learning.domain.content import Challenge, Content
from developer_myself.learning.domain.study_plan import SESSION_EXPIRY, SessionOutcome, StudyPlan
from developer_myself.learning.domain.value_objects import (
    ContentKind,
    ContentStatus,
    MasteryLevel,
)


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddContentIn(_In):
    title: StrictStr = Field(min_length=1, max_length=200)
    kind: ContentKind = ContentKind.BOOK


class RenameContentIn(_In):
    title: StrictStr = Field(min_length=1, max_length=200)


class PreferencesIn(_In):
    minutes_per_day: int = Field(ge=60, le=480, strict=True)
    rest_days: list[int] = Field(default_factory=list, max_length=6)


class ReorderQueueIn(_In):
    content_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class StartSessionIn(_In):
    content_id: uuid.UUID


class FinishSessionIn(_In):
    studied: StrictStr = Field(default="", max_length=10_000)
    understood: StrictStr = Field(default="", max_length=10_000)
    to_review: StrictStr = Field(default="", max_length=10_000)
    recall_rating: int | None = Field(default=None, ge=1, le=4, strict=True)


class AddChallengeIn(_In):
    description: StrictStr = Field(min_length=1, max_length=2_000)
    target_level: MasteryLevel = MasteryLevel.INTERMEDIATE


class SolveChallengeIn(_In):
    evidence: StrictStr = Field(max_length=10_000)


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
            queue_position=position,
            lock_reason=plan.lock_reason(c) if c.status is ContentStatus.LOCKED else None,
            challenges=[ChallengeOut.of(ch) for ch in c.challenges],
        )


class ActiveSessionOut(BaseModel):
    content_id: uuid.UUID
    content_title: str
    kind: str | None
    started_at: datetime
    expires_at: datetime


class PreferencesOut(BaseModel):
    minutes_per_day: int
    rest_days: list[int]


class PlanOut(BaseModel):
    timezone: str
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
                kind=kind.value if kind else None,
                started_at=plan.active_session.started_at,
                expires_at=plan.active_session.started_at + SESSION_EXPIRY,
            )
        reviewed = plan.reviewed_today(now)
        return cls(
            timezone=plan.timezone.name,
            preferences=PreferencesOut(
                minutes_per_day=plan.preferences.minutes_per_day,
                rest_days=sorted(plan.preferences.rest_days),
            ),
            max_in_progress=plan.unlock_policy.max_in_progress,
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
        )


class LevelOut(BaseModel):
    level: MasteryLevel


class UnlockedOut(BaseModel):
    unlocked_content_id: uuid.UUID | None
