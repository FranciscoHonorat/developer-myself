"""Cliente, validadores `$jsonSchema`, índices e TTLs (ADR-0005)."""

from typing import Any

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import CollectionInvalid
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

Doc = dict[str, Any]

PROCESSED_EVENTS_TTL_SECONDS = 30 * 86_400


def make_client(url: str) -> AsyncMongoClient[Doc]:
    return AsyncMongoClient(
        url,
        uuidRepresentation="standard",  # o padrão "unspecified" recusa uuid.UUID
        tz_aware=True,
        w="majority",
        readConcernLevel="majority",
    )


_DATE = {"bsonType": "date"}
_DATE_OR_NULL = {"bsonType": ["date", "null"]}
_UUID = {"bsonType": "binData"}

STUDY_PLAN_SCHEMA: Doc = {
    "bsonType": "object",
    "required": ["_id", "schema_version", "version", "timezone", "contents", "outbox"],
    "properties": {
        "_id": _UUID,
        "schema_version": {"bsonType": "int", "minimum": 1},
        "version": {"bsonType": ["int", "long"], "minimum": 1},
        "timezone": {"bsonType": "string", "maxLength": 64},
        "last_review_on": {"bsonType": ["string", "null"]},
        "has_outbox": {"bsonType": "bool"},
        "active_session": {
            "bsonType": ["object", "null"],
            "required": ["content_id", "started_at"],
            "properties": {
                "content_id": _UUID,
                "started_at": _DATE,
                "questions": {"bsonType": "array"},
            },
        },
        "contents": {
            "bsonType": "array",
            "items": {
                "bsonType": "object",
                "required": ["id", "title", "kind", "status", "points", "queued_at"],
                "properties": {
                    "id": _UUID,
                    "title": {"bsonType": "string", "minLength": 1, "maxLength": 200},
                    "kind": {"enum": ["BOOK", "COURSE", "ARTICLE", "VIDEO", "OTHER"]},
                    "status": {"enum": ["LOCKED", "IN_PROGRESS", "CONSOLIDATED", "FINISHED"]},
                    "points": {"bsonType": "int", "minimum": 0},
                    "queued_at": _DATE,
                    "last_session_at": _DATE_OR_NULL,
                    "finished_at": _DATE_OR_NULL,
                    "last_to_review": {"bsonType": ["string", "null"]},
                    "challenges": {"bsonType": "array"},
                },
            },
        },
        "outbox": {"bsonType": "array"},
    },
}

USER_SCHEMA: Doc = {
    "bsonType": "object",
    "required": ["_id", "email", "password_hash", "created_at"],
    "properties": {
        "_id": _UUID,
        "email": {"bsonType": "string", "maxLength": 254},
        "password_hash": {"bsonType": "string"},
        "created_at": _DATE,
    },
}

AUTH_SESSION_SCHEMA: Doc = {
    "bsonType": "object",
    "required": ["_id", "user_id", "created_at", "expires_at"],
    "properties": {"_id": {"bsonType": "string"}, "user_id": _UUID, "expires_at": _DATE},
}

NOTEBOOK_SCHEMA: Doc = {
    "bsonType": "object",
    "required": ["_id", "learner_id", "text", "version", "updated_at"],
    "properties": {
        "_id": _UUID,
        "learner_id": _UUID,
        # = NOTEBOOK_MAX_CHARS (shared não importa contextos; test_notebook confere).
        "text": {"bsonType": "string", "maxLength": 100_000},
        "version": {"bsonType": ["int", "long"], "minimum": 1},
        "updated_at": _DATE,
    },
}

STUDY_SESSION_SCHEMA: Doc = {
    "bsonType": "object",
    "required": ["_id", "learner_id", "type", "content_id", "started_at", "finished_at"],
    "properties": {"learner_id": {"bsonType": "string"}, "finished_at": _DATE},
}


async def _ensure_collection(db: AsyncDatabase[Doc], name: str, schema: Doc) -> None:
    try:
        await db.create_collection(name, validator={"$jsonSchema": schema})
    except CollectionInvalid:
        await db.command("collMod", name, validator={"$jsonSchema": schema})


async def ensure_schema(db: AsyncDatabase[Doc]) -> None:
    await _ensure_collection(db, "study_plans", STUDY_PLAN_SCHEMA)
    await _ensure_collection(db, "users", USER_SCHEMA)
    await _ensure_collection(db, "auth_sessions", AUTH_SESSION_SCHEMA)
    await _ensure_collection(db, "study_sessions", STUDY_SESSION_SCHEMA)
    await _ensure_collection(db, "processed_events", {"bsonType": "object"})
    await _ensure_collection(db, "notebooks", NOTEBOOK_SCHEMA)
    await _ensure_collection(db, "app_settings", {"bsonType": "object"})

    await db.study_plans.create_indexes(
        [
            IndexModel(
                [("has_outbox", ASCENDING)],
                name="outbox_pending",
                partialFilterExpression={"has_outbox": True},
            )
        ]
    )
    await db.users.create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
            # Listagem do admin: mais recentes primeiro, com desempate pelo id.
            IndexModel([("created_at", DESCENDING), ("_id", DESCENDING)], name="by_created"),
        ]
    )
    await db.auth_sessions.create_indexes(
        [
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expires_at"),
            IndexModel([("user_id", ASCENDING)], name="by_user"),
        ]
    )
    await db.study_sessions.create_indexes(
        [IndexModel([("learner_id", ASCENDING), ("finished_at", DESCENDING)], name="history")]
    )
    await db.notebooks.create_indexes(
        [IndexModel([("learner_id", ASCENDING), ("updated_at", DESCENDING)], name="by_learner")]
    )
    await db.ml_models.create_indexes(
        [IndexModel([("active", ASCENDING), ("created_at", DESCENDING)], name="active_latest")]
    )
    await db.processed_events.create_indexes(
        [
            IndexModel(
                [("seen_at", ASCENDING)],
                expireAfterSeconds=PROCESSED_EVENTS_TTL_SECONDS,
                name="ttl_seen_at",
            )
        ]
    )


def majority(db: AsyncDatabase[Doc]) -> AsyncDatabase[Doc]:
    return db.with_options(
        write_concern=WriteConcern(w="majority"), read_concern=ReadConcern("majority")
    )
