"""Projeção do histórico a partir do envelope do evento."""

import uuid
from datetime import UTC, datetime
from typing import Any

from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.application.history import HistoryQueries, SessionRecord


def finished(**extra: Any) -> dict[str, Any]:
    return {
        "event_id": "e1",
        "learner_id": "l1",
        "type": "study_session_finished",
        "occurred_at": "2026-11-02T12:30:00+00:00",
        "payload": {
            "content_id": "c1",
            "content_title": "Clean Code",
            "kind": "REVIEW",
            "started_at": "2026-11-02T12:00:00+00:00",
            "finished_at": "2026-11-02T12:30:00+00:00",
            "duration_seconds": 1800,
            "awarded": True,
            "withheld_reason": None,
            "notes_studied": "a",
            "notes_understood": "b",
            "notes_to_review": "c",
            "level_after": "INTERMEDIATE",
            **extra,
        },
    }


def test_old_event_without_recall_test_projects_empty_list() -> None:
    assert SessionRecord.from_envelope(finished()).recall_test == []


def test_recall_test_is_projected() -> None:
    item = {"text": "P", "source": "TOPIC", "answer": "r", "grade": "MISSED", "useful": None}
    assert SessionRecord.from_envelope(finished(recall_test=[item])).recall_test == [item]


# ---------------------------------------------------------------- aquecimento
LEARNER = uuid.UUID(int=1)


def warmup_envelope() -> dict[str, Any]:
    item = {"text": "P", "source": "LEARNER", "answer": "r", "grade": "RECALLED", "useful": None}
    return {
        "event_id": "w1",
        "learner_id": str(LEARNER),
        "type": "warmup_finished",
        "occurred_at": "2026-11-02T12:02:00+00:00",
        "payload": {
            "content_id": "c1",
            "content_title": "Clean Code",
            "started_at": "2026-11-02T12:00:00+00:00",
            "finished_at": "2026-11-02T12:02:00+00:00",
            "duration_seconds": 120,
            "recall_test": [item, item],
        },
    }


def test_warmup_envelope_becomes_warmup_record() -> None:
    record = SessionRecord.from_envelope(warmup_envelope())
    assert (record.type, record.kind, record.awarded) == ("warmup_finished", "WARMUP", False)
    assert record.duration_seconds == 120
    assert len(record.recall_test) == 2
    assert not record.is_labeled_review


async def test_stats_ignore_warmups() -> None:
    store = InMemorySessionHistoryStore()
    await store.record(SessionRecord.from_envelope(warmup_envelope()))
    now = datetime(2026, 11, 2, 15, tzinfo=UTC)
    assert await store.list_for(str(LEARNER), 10)  # o aquecimento está no histórico...
    stats = await HistoryQueries(store).stats(LEARNER, "UTC", now)  # ...mas não nas contas
    assert stats.daily[-1].sessions == 0
    assert stats.daily[-1].minutes == 0


async def test_labeled_reviews_ignore_warmups() -> None:
    store = InMemorySessionHistoryStore()
    await store.record(SessionRecord.from_envelope(warmup_envelope()))
    assert await store.labeled_reviews() == []
