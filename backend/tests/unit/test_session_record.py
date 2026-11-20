"""Projeção do histórico a partir do envelope do evento."""

from typing import Any

from developer_myself.insights.application.history import SessionRecord


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
