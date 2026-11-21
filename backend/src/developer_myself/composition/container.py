"""Composition root: o ÚNICO lugar que conhece todos os adapters (ADR-0003)."""

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from developer_myself.accounts.adapters.http import account_routes, admin_routes
from developer_myself.curriculum.domain.unlock import CatalogUnlockPolicy
from developer_myself.identity.adapters.argon2_hasher import Argon2PasswordHasher
from developer_myself.identity.adapters.http import routes as identity_routes
from developer_myself.identity.adapters.memory.repositories import (
    InMemoryAuthSessionRepository,
    InMemoryRegistrationGate,
    InMemoryUserRepository,
)
from developer_myself.identity.application.ports import PasswordHasher
from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import (
    CannotDeleteSelfError,
    EmailAlreadyRegisteredError,
    IdentityError,
    InvalidCredentialsError,
    InvalidUsernameError,
    NotAdminError,
    NotAuthenticatedError,
    RegistrationClosedError,
    UsernameTakenError,
    UserNotFoundError,
    parse_admin_emails,
)
from developer_myself.insights.adapters import http_routes as insights_routes
from developer_myself.insights.adapters.memory.model_registry import InMemoryModelRegistry
from developer_myself.insights.adapters.memory.store import InMemorySessionHistoryStore
from developer_myself.insights.adapters.neural.provider import RecommenderProvider
from developer_myself.insights.adapters.neural.recommender import load_best_recommender
from developer_myself.insights.adapters.neural.retrain import RetrainJob
from developer_myself.insights.application.history import HistoryQueries, RecordSessionHistory
from developer_myself.learning.adapters.curriculum.question_picker import RuleQuestionPicker
from developer_myself.learning.adapters.http import routes as learning_routes
from developer_myself.learning.adapters.memory.notebook_repository import (
    InMemoryNotebookRepository,
)
from developer_myself.learning.adapters.memory.repository import InMemoryStudyPlanRepository
from developer_myself.learning.application.use_cases import LearningUseCases
from developer_myself.learning.domain.errors import (
    ChallengeNotFoundError,
    ConcurrencyError,
    ContentNotFoundError,
    DomainError,
    InvalidValueError,
    StudyPlanNotFoundError,
)
from developer_myself.learning.domain.value_objects import LearnerId
from developer_myself.planning.adapters.http import (
    competency_routes,
    recommendation_routes,
    schedule_routes,
)
from developer_myself.shared.adapters.http import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    rate_limit_rules,
)
from developer_myself.shared.adapters.rate_limit import SlidingWindowLimiter
from developer_myself.shared.clock import Clock, SystemClock
from developer_myself.shared.logging import configure_logging, log
from developer_myself.shared.settings import Settings

Check = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class Container:
    settings: Settings
    clock: Clock
    learning: LearningUseCases
    identity: IdentityUseCases
    history: HistoryQueries
    record_history: RecordSessionHistory
    erase_learner_data: Callable[[uuid.UUID], Awaitable[None]]
    recommender: RecommenderProvider
    retrain_job: RetrainJob
    readiness_checks: dict[str, Check] = field(default_factory=dict)
    closers: list[Callable[[], Awaitable[None]]] = field(default_factory=list)

    async def close(self) -> None:
        for closer in reversed(self.closers):
            await closer()


def build_memory_container(
    settings: Settings, clock: Clock | None = None, hasher: PasswordHasher | None = None
) -> Container:
    clock = clock or SystemClock()
    store = InMemorySessionHistoryStore()
    record = RecordSessionHistory(store)
    plans = InMemoryStudyPlanRepository(subscribers=[record])
    notebooks = InMemoryNotebookRepository()
    registry = InMemoryModelRegistry()
    identity = IdentityUseCases(
        InMemoryUserRepository(),
        InMemoryAuthSessionRepository(),
        hasher or Argon2PasswordHasher(),
        clock,
        timedelta(days=settings.session_ttl_days),
        registration=InMemoryRegistrationGate(),
        admin_emails=parse_admin_emails(settings.admin_emails),
    )

    async def erase(learner_id: uuid.UUID) -> None:
        await plans.delete(LearnerId(learner_id))
        await store.delete_for(str(learner_id))
        await notebooks.delete_all(LearnerId(learner_id))

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
        identity=identity,
        history=HistoryQueries(store),
        record_history=record,
        erase_learner_data=erase,
        recommender=RecommenderProvider(load_best_recommender(), registry, refresh_seconds=0),
        retrain_job=RetrainJob(
            store, registry, clock, min_new_labels=settings.retrain_min_new_labels
        ),
    )


async def build_container(settings: Settings) -> Container:
    if settings.storage == "memory":
        return build_memory_container(settings)
    from developer_myself.composition.mongo import build_mongo_container  # noqa: PLC0415

    return await build_mongo_container(settings)


# --------------------------------------------------------------------------- erros → HTTP

_NOT_FOUND = (ContentNotFoundError, ChallengeNotFoundError, StudyPlanNotFoundError)


def _error(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc), "code": type(exc).__name__}, status_code=status_code)


STABLE_ERROR_CODES: dict[type[IdentityError], tuple[int, str]] = {
    NotAdminError: (403, "FORBIDDEN"),
    RegistrationClosedError: (403, "REGISTRATION_CLOSED"),
    CannotDeleteSelfError: (409, "CANNOT_DELETE_SELF"),
    UserNotFoundError: (404, "NOT_FOUND"),
    UsernameTakenError: (409, "USERNAME_TAKEN"),
    InvalidUsernameError: (422, "INVALID_USERNAME"),
}


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        if isinstance(exc, _NOT_FOUND):
            return _error(404, exc)
        if isinstance(exc, InvalidValueError):
            return _error(422, exc)
        return _error(409, exc)

    @app.exception_handler(ConcurrencyError)
    async def concurrency_error(_: Request, _exc: ConcurrencyError) -> JSONResponse:
        return JSONResponse(
            {"detail": "A trilha mudou em outra aba. Tente de novo.", "code": "ConcurrencyError"},
            status_code=409,
        )

    @app.exception_handler(IdentityError)
    async def identity_error(_: Request, exc: IdentityError) -> JSONResponse:
        # Erros com `code` estável: o frontend decide a mensagem por ele.
        for kind, (status_code, code) in STABLE_ERROR_CODES.items():
            if isinstance(exc, kind):
                return JSONResponse({"detail": str(exc), "code": code}, status_code=status_code)
        if isinstance(exc, InvalidCredentialsError | NotAuthenticatedError):
            return _error(401, exc)
        if isinstance(exc, EmailAlreadyRegisteredError):
            return _error(409, exc)
        return _error(422, exc)

    @app.exception_handler(HTTPException)
    async def http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        body = (
            exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail, "code": "HTTP"}
        )
        return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)


# --------------------------------------------------------------------------- app


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level, json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        built = container or await build_container(settings)
        app.state.container = built
        app.state.authenticate = _authenticator(built)
        # Antes de aceitar login: conta antiga sem username ficaria trancada para fora.
        if filled := await built.identity.assign_missing_usernames():
            log.warning("usernames_assigned", count=filled)
        log.info("api_started", storage=settings.storage)
        if missing := await built.identity.admin_emails_without_account():
            # Sem o e-mail no log: só quantos. Quem cadastrar esse e-mail primeiro vira admin.
            log.warning("admin_email_without_account", count=missing)
        try:
            yield
        finally:
            await built.close()

    app = FastAPI(title="Developer Myself", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.login_limiter = SlidingWindowLimiter(max_hits=10, window_seconds=60)
    if container is not None:  # testes sem lifespan
        app.state.container = container
        app.state.authenticate = _authenticator(container)
    # O último adicionado é o mais externo: o 429 ainda ganha correlation id e cabeçalhos.
    app.add_middleware(RateLimitMiddleware, rules=rate_limit_rules(settings))
    app.add_middleware(RequestContextMiddleware)
    _install_error_handlers(app)

    for module in (
        identity_routes,
        admin_routes,
        learning_routes,
        insights_routes,
        account_routes,
        recommendation_routes,
        schedule_routes,
        competency_routes,
    ):
        app.include_router(module.router)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> JSONResponse:
        checks: dict[str, str] = {}
        for name, check in request.app.state.container.readiness_checks.items():
            try:
                await check()
                checks[name] = "ok"
            except Exception as exc:
                checks[name] = f"erro: {type(exc).__name__}"
        ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            {"status": "ok" if ok else "degraded", "checks": checks}, 200 if ok else 503
        )

    if settings.static_dir:
        _mount_spa(app, Path(settings.static_dir))
    return app


def _authenticator(container: Container) -> Callable[[str | None], Awaitable[uuid.UUID]]:
    async def authenticate(token: str | None) -> uuid.UUID:
        user_id = await container.identity.authenticate(token)
        return user_id.value

    return authenticate


def _mount_spa(app: FastAPI, root: Path) -> None:
    """Serve o build do React na MESMA origem da API (cookie SameSite=Strict, ADR-0009)."""
    index = root / "index.html"
    resolved_root = root.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404, {"detail": "Não encontrado.", "code": "NotFound"})
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(resolved_root):
            return FileResponse(candidate)
        return FileResponse(index)
