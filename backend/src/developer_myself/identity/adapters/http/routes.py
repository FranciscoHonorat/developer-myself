"""Cadastro, login e logout com cookie de sessão opaco (ADR-0009)."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import User, UserId
from developer_myself.shared.adapters.http import LearnerIdDep, http_error
from developer_myself.shared.settings import Settings


class CredentialsIn(BaseModel):
    """Login: só username + senha (`extra="forbid"`: mandar `email` é 422)."""

    model_config = ConfigDict(extra="forbid")
    username: StrictStr = Field(max_length=64)
    password: StrictStr = Field(max_length=256)


class RegisterIn(CredentialsIn):
    email: StrictStr = Field(max_length=254)
    timezone: StrictStr = Field(default="America/Sao_Paulo", max_length=64)


class ChangeUsernameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: StrictStr = Field(max_length=64)
    password: StrictStr = Field(max_length=256)


class PasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: StrictStr = Field(max_length=256)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    username: str | None = None
    is_admin: bool = False

    @classmethod
    def of(cls, user: User, uc: IdentityUseCases) -> MeOut:
        return cls(
            id=user.id.value,
            email=user.email.value,
            created_at=user.created_at,
            username=user.username.value if user.username else None,
            is_admin=user.email in uc.admin_emails,
        )


class RegistrationOut(BaseModel):
    open: bool


def get_identity(request: Request) -> IdentityUseCases:
    uc: IdentityUseCases = request.app.state.container.identity
    return uc


Identity = Annotated[IdentityUseCases, Depends(get_identity)]
router = APIRouter(prefix="/api/auth", tags=["identity"])


def _set_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.session_ttl_days * 86_400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def _delete_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _validate_timezone(name: str) -> None:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Fuso horário desconhecido: {name!r}.",
            "InvalidValueError",
        ) from exc


async def _login(
    request: Request, response: Response, uc: IdentityUseCases, body: CredentialsIn
) -> None:
    client = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_limiter
    # Chave por IP e por par (IP + username normalizado): impede brute-force sem permitir
    # que um atacante em outros IPs tranque (DoS) a conta da vítima.
    pair_key = f"pair:{client}:{body.username.strip().lower()}"
    if not limiter.allow(f"ip:{client}") or not limiter.allow(pair_key):
        raise http_error(
            status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Aguarde.", "RATE_LIMIT"
        )
    token, _ = await uc.login(body.username, body.password)
    limiter.reset(pair_key)
    _set_cookie(response, request.app.state.settings, token.raw)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, response: Response, uc: Identity) -> MeOut:
    _validate_timezone(body.timezone)
    user = await uc.register(body.username, body.email, body.password)
    # Composição entre contextos só por ID: a trilha nasce com o id do usuário.
    # Se a criação da trilha falhar, compensa removendo a conta para não deixar usuário órfão.
    try:
        await request.app.state.container.learning.create_plan(user.id.value, body.timezone)
    except Exception:
        await uc.users.delete(user.id)
        raise
    await _login(request, response, uc, body)
    return MeOut.of(user, uc)


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(body: CredentialsIn, request: Request, response: Response, uc: Identity) -> None:
    await _login(request, response, uc, body)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, uc: Identity) -> None:
    settings: Settings = request.app.state.settings
    await uc.logout(request.cookies.get(settings.cookie_name))
    _delete_cookie(response, settings)


@router.get("/me")
async def me(learner_id: LearnerIdDep, uc: Identity) -> MeOut:
    return MeOut.of(await uc.me(UserId(learner_id)), uc)


@router.put("/username")
async def change_username(body: ChangeUsernameIn, learner_id: LearnerIdDep, uc: Identity) -> MeOut:
    """Troca o próprio username (pede a senha). A sessão atual continua válida."""
    user = await uc.change_username(UserId(learner_id), body.username, body.password)
    return MeOut.of(user, uc)


@router.get("/registration")
async def registration_status(uc: Identity) -> RegistrationOut:
    """Público: `/cadastro` avisa antes de a pessoa preencher o formulário."""
    return RegistrationOut(open=await uc.registration_open())


EraseData = Callable[[uuid.UUID], Awaitable[None]]


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: PasswordIn, request: Request, response: Response, learner_id: LearnerIdDep, uc: Identity
) -> None:
    """LGPD: exclui trilha, histórico, cadernos e, por último, sessões e conta.

    Apagar os dados de estudo antes da conta garante que, se ocorrer erro no meio, a
    sessão continua válida para o usuário tentar de novo sem deixar dados órfãos.
    """
    user_id = UserId(learner_id)
    await uc.verify_password(user_id, body.password)
    erase: EraseData = request.app.state.container.erase_learner_data
    await erase(learner_id)
    await uc.finalize_delete_account(user_id)
    _delete_cookie(response, request.app.state.settings)
