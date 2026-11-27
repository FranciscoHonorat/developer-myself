"""Adapter Mongo do `StudyPlan`: 1 agregado = 1 documento (ADR-0005).

- Optimistic lock pelo campo `version`.
- Outbox embutido: eventos vão no MESMO update atômico (`$push`) do estado (ADR-0006).
- Sem ODM: o mapeamento domínio ⇄ documento fica todo aqui.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from developer_myself.learning.domain.content import Challenge, Content
from developer_myself.learning.domain.errors import ConcurrencyError
from developer_myself.learning.domain.study_plan import ActiveSession, ActiveWarmup, StudyPlan
from developer_myself.learning.domain.value_objects import (
    ChallengeId,
    ContentId,
    ContentKind,
    ContentStatus,
    Evidence,
    LearnerId,
    LearnerQuestion,
    MasteryLevel,
    Points,
    Purpose,
    QuestionSource,
    RecallQuestion,
    RecallRating,
    StudyPreferences,
    Timezone,
    Title,
)
from developer_myself.shared.correlation import get_correlation_id
from developer_myself.shared.events import envelope

SCHEMA_VERSION = 6
Doc = dict[str, Any]


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _opt_utc(value: datetime | None) -> datetime | None:
    return _utc(value) if value is not None else None


# --------------------------------------------------------------------------- mapper


def _question_doc(q: RecallQuestion) -> Doc:
    return {
        "id": q.id,
        "text": q.text,
        "source": q.source.value,
        "template": q.template,
        "topic": q.topic,
        "expected_answer": q.expected_answer,
    }


def _question(q: Doc) -> RecallQuestion:
    return RecallQuestion(
        id=q["id"],
        text=q["text"],
        source=QuestionSource(q["source"]),
        template=q["template"],
        topic=q.get("topic"),
        expected_answer=q.get("expected_answer"),
    )


def to_document(plan: StudyPlan) -> Doc:
    """Estado do agregado (sem `version` e sem `outbox`, que têm tratamento próprio)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "timezone": plan.timezone.name,
        "purpose": plan.purpose.value if plan.purpose else None,
        "max_in_progress": plan.max_in_progress,
        "preferences": {
            "minutes_per_day": plan.preferences.minutes_per_day,
            "rest_days": sorted(plan.preferences.rest_days),
        },
        "last_review_on": plan.last_review_on.isoformat() if plan.last_review_on else None,
        "active_session": (
            {
                "content_id": plan.active_session.content_id.value,
                "started_at": plan.active_session.started_at,
                "questions": [_question_doc(q) for q in plan.active_session.questions],
            }
            if plan.active_session
            else None
        ),
        "active_warmup": (
            {
                "content_id": plan.active_warmup.content_id.value,
                "started_at": plan.active_warmup.started_at,
                "questions": [_question_doc(q) for q in plan.active_warmup.questions],
            }
            if plan.active_warmup
            else None
        ),
        "last_warmup_on": plan.last_warmup_on.isoformat() if plan.last_warmup_on else None,
        "contents": [
            {
                "id": c.id.value,
                "title": c.title.value,
                "kind": c.kind.value,
                "status": c.status.value,
                "points": c.points.value,
                "queued_at": c.queued_at,
                "last_session_at": c.last_session_at,
                "finished_at": c.finished_at,
                "first_session_at": c.first_session_at,
                "session_count": c.session_count,
                "review_count": c.review_count,
                "notes_chars_total": c.notes_chars_total,
                "last_recall_rating": int(c.last_recall_rating) if c.last_recall_rating else None,
                "consolidated_at": c.consolidated_at,
                "last_to_review": c.last_to_review,
                "purpose": c.purpose.value if c.purpose else None,
                "learner_questions": [
                    {"id": q.id, "text": q.text, "answer": q.answer, "created_at": q.created_at}
                    for q in c.learner_questions
                ],
                "challenges": [
                    {
                        "id": ch.id.value,
                        "description": ch.description,
                        "target_level": ch.target_level.value,
                        "created_at": ch.created_at,
                        "solved_at": ch.solved_at,
                        "evidence": ch.evidence.value if ch.evidence else None,
                    }
                    for ch in c.challenges
                ],
            }
            for c in plan.contents
        ],
    }


def _v1_to_v2(doc: Doc) -> Doc:
    """v2: contadores de memória por conteúdo (features da rede neural, ADR-0012)."""
    for content in doc["contents"]:
        content.setdefault("first_session_at", content.get("last_session_at"))
        content.setdefault("session_count", 1 if content.get("last_session_at") else 0)
        content.setdefault("review_count", 0)
        content.setdefault("notes_chars_total", 0)
        content.setdefault("last_recall_rating", None)
    doc["schema_version"] = 2
    return doc


def _v2_to_v3(doc: Doc) -> Doc:
    """v3: preferências de estudo (minutos por dia e dias de folga)."""
    doc.setdefault("preferences", {"minutes_per_day": 210, "rest_days": []})
    doc["schema_version"] = 3
    return doc


def _v3_to_v4(doc: Doc) -> Doc:
    """v4: teste de memória da revisão e o último "preciso revisar" de cada conteúdo."""
    for content in doc["contents"]:
        content.setdefault("last_to_review", None)
    if doc.get("active_session"):
        doc["active_session"].setdefault("questions", [])
    doc["schema_version"] = 4
    return doc


def _v4_to_v5(doc: Doc) -> Doc:
    """v5: aquecimento (ativo e último dia) e perguntas do aprendiz para o "eu do futuro"."""
    doc.setdefault("active_warmup", None)
    doc.setdefault("last_warmup_on", None)
    for content in doc["contents"]:
        content.setdefault("learner_questions", [])
    if doc.get("active_session"):
        for question in doc["active_session"]["questions"]:
            question.setdefault("expected_answer", None)
    doc["schema_version"] = 5
    return doc


def _v5_to_v6(doc: Doc) -> Doc:
    """v6: SDT — propósito (plano e conteúdos) e limite próprio de conteúdos em paralelo."""
    doc.setdefault("purpose", None)
    doc.setdefault("max_in_progress", None)
    for content in doc["contents"]:
        content.setdefault("purpose", None)
    doc["schema_version"] = 6
    return doc


UPCASTERS = {1: _v1_to_v2, 2: _v2_to_v3, 3: _v3_to_v4, 4: _v4_to_v5, 5: _v5_to_v6}


def upcast(doc: Doc) -> Doc:
    """Migração lazy: atualiza documentos antigos na leitura, um degrau por vez (ADR-0005).

    O documento é regravado já na versão nova no próximo `save`.
    """
    version = doc.get("schema_version", 1)
    if version > SCHEMA_VERSION:
        raise ValueError(f"schema_version {version} é mais nova que este código.")
    while version < SCHEMA_VERSION:
        doc = UPCASTERS[version](doc)
        version = doc["schema_version"]
    return doc


def from_document(doc: Doc) -> StudyPlan:
    doc = upcast(doc)
    active = doc.get("active_session")
    warmup = doc.get("active_warmup")
    plan = StudyPlan(
        id=LearnerId(doc["_id"]),
        timezone=Timezone(doc["timezone"]),
        contents=[
            Content(
                id=ContentId(c["id"]),
                title=Title(c["title"]),
                kind=ContentKind(c["kind"]),
                status=ContentStatus(c["status"]),
                queued_at=_utc(c["queued_at"]),
                points=Points(c["points"]),
                last_session_at=_opt_utc(c.get("last_session_at")),
                finished_at=_opt_utc(c.get("finished_at")),
                first_session_at=_opt_utc(c.get("first_session_at")),
                session_count=c["session_count"],
                review_count=c["review_count"],
                notes_chars_total=c["notes_chars_total"],
                last_recall_rating=(
                    RecallRating(c["last_recall_rating"]) if c.get("last_recall_rating") else None
                ),
                consolidated_at=_opt_utc(c.get("consolidated_at")),
                last_to_review=c["last_to_review"],
                purpose=Purpose(c["purpose"]) if c.get("purpose") else None,
                learner_questions=tuple(
                    LearnerQuestion(
                        id=q["id"],
                        text=q["text"],
                        created_at=_utc(q["created_at"]),
                        answer=q.get("answer"),
                    )
                    for q in c["learner_questions"]
                ),
                challenges=[
                    Challenge(
                        id=ChallengeId(ch["id"]),
                        description=ch["description"],
                        target_level=MasteryLevel(ch["target_level"]),
                        created_at=_utc(ch["created_at"]),
                        solved_at=_opt_utc(ch.get("solved_at")),
                        evidence=Evidence(ch["evidence"]) if ch.get("evidence") else None,
                    )
                    for ch in c.get("challenges", [])
                ],
            )
            for c in doc["contents"]
        ],
        active_session=(
            ActiveSession(
                ContentId(active["content_id"]),
                _utc(active["started_at"]),
                tuple(_question(q) for q in active["questions"]),
            )
            if active
            else None
        ),
        active_warmup=(
            ActiveWarmup(
                ContentId(warmup["content_id"]),
                _utc(warmup["started_at"]),
                tuple(_question(q) for q in warmup["questions"]),
            )
            if warmup
            else None
        ),
        last_warmup_on=(
            date.fromisoformat(doc["last_warmup_on"]) if doc.get("last_warmup_on") else None
        ),
        last_review_on=(
            date.fromisoformat(doc["last_review_on"]) if doc.get("last_review_on") else None
        ),
        version=doc["version"],
        preferences=StudyPreferences(
            doc["preferences"]["minutes_per_day"], frozenset(doc["preferences"]["rest_days"])
        ),
        purpose=Purpose(doc["purpose"]) if doc.get("purpose") else None,
        max_in_progress=doc.get("max_in_progress"),
    )
    return plan


def outbox_entry(event_envelope: Doc) -> Doc:
    entry = dict(event_envelope)
    entry["event_id"] = uuid.UUID(entry["event_id"])
    return entry


# --------------------------------------------------------------------------- repositório


class MongoStudyPlanRepository:
    def __init__(self, collection: AsyncCollection[Doc]) -> None:
        self._col = collection

    async def get(self, learner_id: LearnerId) -> StudyPlan | None:
        doc = await self._col.find_one({"_id": learner_id.value}, {"outbox": 0})
        return from_document(doc) if doc is not None else None

    async def save(self, plan: StudyPlan) -> None:
        events = plan.pending_events
        cid = get_correlation_id()
        outbox = [outbox_entry(envelope(e, cid)) for e in events]
        state = to_document(plan)

        if plan.version == 0:
            try:
                await self._col.insert_one(
                    {
                        "_id": plan.id.value,
                        **state,
                        "version": 1,
                        "outbox": outbox,
                        "has_outbox": bool(outbox),
                    }
                )
            except DuplicateKeyError as exc:
                raise ConcurrencyError(f"Trilha {plan.id} já existe.") from exc
        else:
            update: Doc = {"$set": state, "$inc": {"version": 1}}
            if outbox:
                update["$set"] = {**state, "has_outbox": True}
                update["$push"] = {"outbox": {"$each": outbox}}
            result = await self._col.update_one(
                {"_id": plan.id.value, "version": plan.version}, update
            )
            if result.matched_count == 0:
                raise ConcurrencyError(f"Trilha {plan.id} mudou desde a leitura.")

        plan.pull_events()
        plan.version += 1

    async def delete(self, learner_id: LearnerId) -> None:
        await self._col.delete_one({"_id": learner_id.value})

    async def content_counts(self, learner_ids: list[LearnerId]) -> dict[LearnerId, int]:
        if not learner_ids:
            return {}
        pipeline: list[Doc] = [
            {"$match": {"_id": {"$in": [lid.value for lid in learner_ids]}}},
            {"$project": {"count": {"$size": "$contents"}}},
        ]
        cursor = await self._col.aggregate(pipeline)
        return {LearnerId(doc["_id"]): int(doc["count"]) async for doc in cursor}
