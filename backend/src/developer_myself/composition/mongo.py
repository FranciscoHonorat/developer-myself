"""Composition root da infraestrutura real: Mongo (+ RabbitMQ no worker)."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta

from pymongo import AsyncMongoClient

from developer_myself.composition.container import Container
from developer_myself.curriculum.domain.unlock import CatalogUnlockPolicy
from developer_myself.identity.adapters.argon2_hasher import Argon2PasswordHasher
from developer_myself.identity.adapters.mongo.repositories import (
    MongoAuthSessionRepository,
    MongoRegistrationGate,
    MongoUserRepository,
)
from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import parse_admin_emails
from developer_myself.insights.adapters.mongo.model_registry import MongoModelRegistry
from developer_myself.insights.adapters.mongo.store import MongoSessionHistoryStore
from developer_myself.insights.adapters.neural.provider import RecommenderProvider
from developer_myself.insights.adapters.neural.recommender import load_best_recommender
from developer_myself.insights.adapters.neural.retrain import RetrainJob
from developer_myself.insights.application.history import HistoryQueries, RecordSessionHistory
from developer_myself.learning.adapters.curriculum.question_picker import RuleQuestionPicker
from developer_myself.learning.adapters.mongo.notebook_repository import MongoNotebookRepository
from developer_myself.learning.adapters.mongo.repository import MongoStudyPlanRepository
from developer_myself.learning.application.use_cases import LearningUseCases
from developer_myself.learning.domain.value_objects import LearnerId
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client
from developer_myself.shared.clock import Clock, SystemClock
from developer_myself.shared.settings import Settings


async def build_mongo_container(
    settings: Settings,
    clock: Clock | None = None,
    *,
    client: AsyncMongoClient[Doc] | None = None,
) -> Container:
    clock = clock or SystemClock()
    owns_client = client is None
    mongo_client = client or make_client(settings.mongo_url.get_secret_value())
    db = mongo_client[settings.mongo_db]
    await ensure_schema(db)

    plans = MongoStudyPlanRepository(db.study_plans)
    notebooks = MongoNotebookRepository(db.notebooks)
    store = MongoSessionHistoryStore(db.study_sessions, db.processed_events)
    users = MongoUserRepository(db.users)
    auth_sessions = MongoAuthSessionRepository(db.auth_sessions)
    registry = MongoModelRegistry(db.ml_models)

    async def erase(learner_id: uuid.UUID) -> None:
        await plans.delete(LearnerId(learner_id))
        await store.delete_for(str(learner_id))
        await notebooks.delete_all(LearnerId(learner_id))

    async def ping_mongo() -> None:
        await mongo_client.admin.command("ping")

    async def close_mongo() -> None:
        await mongo_client.close()

    closers: list[Callable[[], Awaitable[None]]] = [close_mongo] if owns_client else []

    return Container(
        settings=settings,
        clock=clock,
        learning=LearningUseCases.build(
            plans,
            clock,
            CatalogUnlockPolicy(settings.max_parallel_contents),
            notebooks=notebooks,
            question_picker=RuleQuestionPicker(),
        ),
        identity=IdentityUseCases(
            users,
            auth_sessions,
            Argon2PasswordHasher(),
            clock,
            timedelta(days=settings.session_ttl_days),
            registration=MongoRegistrationGate(db.app_settings),
            admin_emails=parse_admin_emails(settings.admin_emails),
        ),
        history=HistoryQueries(store),
        record_history=RecordSessionHistory(store),
        erase_learner_data=erase,
        recommender=RecommenderProvider(
            load_best_recommender(), registry, refresh_seconds=settings.model_reload_seconds
        ),
        retrain_job=RetrainJob(
            store, registry, clock, min_new_labels=settings.retrain_min_new_labels
        ),
        readiness_checks={"mongo": ping_mongo},
        closers=closers,
    )
