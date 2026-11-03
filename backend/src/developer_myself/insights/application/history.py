"""Contexto de suporte `insights`: projeção do histórico de sessões (ADR-0006, ADR-0012).

Recebe envelopes (dicionários) — nunca importa o modelo do `learning`.
"""

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

HISTORY_EVENT_TYPES = frozenset({"study_session_finished", "study_session_abandoned"})


@dataclass(frozen=True, slots=True)
class SessionRecord:
    event_id: str
    learner_id: str
    type: str
    content_id: str
    content_title: str
    kind: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: int
    awarded: bool
    reason: str | None
    notes_studied: str
    notes_understood: str
    notes_to_review: str
    level_after: str | None
    # Rótulo real (autoavaliação) + sinais de antes da sessão (dataset da rede, ADR-0012).
    recall_rating: int | None = None
    level_before: str | None = None
    last_contact_days: float | None = None
    points_before: int = 0
    challenges_solved_before: int = 0
    review_count_before: int = 0
    days_since_first_session: float | None = None
    avg_notes_chars_before: float = 0.0
    last_recall_rating_before: int | None = None

    @property
    def is_labeled_review(self) -> bool:
        return (
            self.type == "study_session_finished"
            and self.kind == "REVIEW"
            and self.recall_rating is not None
            and self.last_contact_days is not None
        )

    @classmethod
    def from_envelope(cls, envelope: dict[str, Any]) -> SessionRecord:
        p = envelope["payload"]
        started = datetime.fromisoformat(p["started_at"])
        if envelope["type"] == "study_session_finished":
            finished = datetime.fromisoformat(p["finished_at"])
            return cls(
                event_id=envelope["event_id"],
                learner_id=envelope["learner_id"],
                type=envelope["type"],
                content_id=p["content_id"],
                content_title=p["content_title"],
                kind=p["kind"],
                started_at=started,
                finished_at=finished,
                duration_seconds=p["duration_seconds"],
                awarded=p["awarded"],
                reason=p["withheld_reason"],
                notes_studied=p["notes_studied"],
                notes_understood=p["notes_understood"],
                notes_to_review=p["notes_to_review"],
                level_after=p["level_after"],
                recall_rating=p.get("recall_rating"),
                level_before=p.get("level_before"),
                last_contact_days=p.get("last_contact_days"),
                points_before=p.get("points_before", 0),
                challenges_solved_before=p.get("challenges_solved_before", 0),
                review_count_before=p.get("review_count_before", 0),
                days_since_first_session=p.get("days_since_first_session"),
                avg_notes_chars_before=p.get("avg_notes_chars_before", 0.0),
                last_recall_rating_before=p.get("last_recall_rating_before"),
            )
        occurred = datetime.fromisoformat(envelope["occurred_at"])
        return cls(
            event_id=envelope["event_id"],
            learner_id=envelope["learner_id"],
            type=envelope["type"],
            content_id=p["content_id"],
            content_title=p["content_title"],
            kind=p["kind"],
            started_at=started,
            finished_at=occurred,
            duration_seconds=int((occurred - started).total_seconds()),
            awarded=False,
            reason=p["reason"],
            notes_studied="",
            notes_understood="",
            notes_to_review="",
            level_after=None,
        )


class SessionHistoryStore(Protocol):
    async def record(self, record: SessionRecord) -> bool:
        """Grava de forma idempotente (chave = event_id). Retorna False se já existia."""
        ...

    async def list_for(
        self, learner_id: str, limit: int, since: datetime | None = None
    ) -> list[SessionRecord]: ...

    async def delete_for(self, learner_id: str) -> None: ...

    async def labeled_reviews(self, limit: int = 100_000) -> list[SessionRecord]:
        """Revisões com autoavaliação, de todos os aprendizes: o dataset real de treino."""
        ...


@dataclass(slots=True)
class RecordSessionHistory:
    """Handler do consumer: idempotente, então at-least-once é seguro."""

    store: SessionHistoryStore

    async def __call__(self, envelope: dict[str, Any]) -> bool:
        if envelope.get("type") not in HISTORY_EVENT_TYPES:
            return False
        return await self.store.record(SessionRecord.from_envelope(envelope))


@dataclass(frozen=True, slots=True)
class DailyStat:
    day: date
    sessions: int
    minutes: int
    points: int


@dataclass(frozen=True, slots=True)
class Stats:
    total_sessions: int
    total_points: int
    total_minutes: int
    current_streak_days: int
    withheld_by_reason: dict[str, int]
    daily: list[DailyStat]


@dataclass(slots=True)
class HistoryQueries:
    store: SessionHistoryStore

    async def recent(self, learner_id: uuid.UUID, limit: int = 50) -> list[SessionRecord]:
        return await self.store.list_for(str(learner_id), limit)

    async def stats(
        self, learner_id: uuid.UUID, timezone: str, now: datetime, days: int = 30
    ) -> Stats:
        tz = ZoneInfo(timezone)
        records = await self.store.list_for(
            str(learner_id), limit=5_000, since=now - timedelta(days=days)
        )
        finished = [r for r in records if r.type == "study_session_finished"]
        by_day: dict[date, list[SessionRecord]] = {}
        for r in finished:
            by_day.setdefault(r.finished_at.astimezone(tz).date(), []).append(r)
        today = now.astimezone(tz).date()
        daily = [
            DailyStat(
                day=d,
                sessions=len(by_day.get(d, [])),
                minutes=sum(r.duration_seconds for r in by_day.get(d, [])) // 60,
                points=sum(1 for r in by_day.get(d, []) if r.awarded),
            )
            for d in (today - timedelta(days=i) for i in range(days - 1, -1, -1))
        ]
        streak = 0
        for stat in reversed(daily):
            if stat.points > 0:
                streak += 1
            elif stat.day != today:
                break
        withheld = Counter(r.reason for r in records if r.reason)
        return Stats(
            total_sessions=len(finished),
            total_points=sum(1 for r in finished if r.awarded),
            total_minutes=sum(r.duration_seconds for r in finished) // 60,
            current_streak_days=streak,
            withheld_by_reason=dict(withheld),
            daily=daily,
        )
