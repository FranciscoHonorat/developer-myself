"""Cadastro, login e logout com cookie de sessão opaco (ADR-0009)."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import UserId
from developer_myself.shared.adapters.http import LearnerIdDep, http_error
from developer_myself.shared.settings import Settings


class CredentialsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: StrictStr = Field(max_length=254)
    password: StrictStr = Field(max_length=256)


class RegisterIn(CredentialsIn):
    timezone: StrictStr = Field(default="America/Sao_Paulo", max_length=64)


class PasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: StrictStr = Field(max_length=256)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    is_admin: bool = False


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


async def _login(
    request: Request, response: Response, uc: IdentityUseCases, body: CredentialsIn
) -> None:
    client = request.client.host if request.client else "unknown"
    limiter = request.app.state.login_limiter
    if not limiter.allow(f"ip:{client}") or not limiter.allow(f"email:{body.email.lower()}"):
        raise http_error(
            status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Aguarde.", "RATE_LIMIT"
        )
    token, _ = await uc.login(body.email, body.password)
    limiter.reset(f"email:{body.email.lower()}")
    _set_cookie(response, request.app.state.settings, token.raw)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, response: Response, uc: Identity) -> MeOut:
    user = await uc.register(body.email, body.password)
    # Composição entre contextos só por ID: a trilha nasce com o id do usuário.
    await request.app.state.container.learning.create_plan(user.id.value, body.timezone)
    await _login(request, response, uc, body)
    return MeOut(id=user.id.value, email=user.email.value, created_at=user.created_at)


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(body: CredentialsIn, request: Request, response: Response, uc: Identity) -> None:
    await _login(request, response, uc, body)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, uc: Identity) -> None:
    settings: Settings = request.app.state.settings
    await uc.logout(request.cookies.get(settings.cookie_name))
    response.delete_cookie(settings.cookie_name, path="/")


@router.get("/me")
async def me(learner_id: LearnerIdDep, uc: Identity) -> MeOut:
    user = await uc.me(UserId(learner_id))
    return MeOut(
        id=user.id.value,
        email=user.email.value,
        created_at=user.created_at,
        is_admin=user.email in uc.admin_emails,
    )


@router.get("/registration")
async def registration_status(uc: Identity) -> RegistrationOut:
    """Público: `/cadastro` avisa antes de a pessoa preencher o formulário."""
    return RegistrationOut(open=await uc.registration_open())


EraseData = Callable[[uuid.UUID], Awaitable[None]]


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    body: PasswordIn, request: Request, response: Response, learner_id: LearnerIdDep, uc: Identity
) -> None:
    """LGPD: exclui conta, trilha e histórico."""
    await uc.delete_account(UserId(learner_id), body.password)
    erase: EraseData = request.app.state.container.erase_learner_data
    await erase(learner_id)
    response.delete_cookie(request.app.state.settings.cookie_name, path="/")
