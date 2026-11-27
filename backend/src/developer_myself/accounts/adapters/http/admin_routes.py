"""Área de admin: compõe identity + learning + insights só por IDs (ADR-0003).

Quem é admin vem de `DM_ADMIN_EMAILS`. O admin vê só contagens de outras contas, nunca
anotações, caderno ou histórico.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, StrictBool

from developer_myself.identity.domain.model import User, UserCursor, UserId, UserNotFoundError
from developer_myself.shared.adapters.cursor import decode_cursor, encode_cursor
from developer_myself.shared.adapters.http import LearnerIdDep, http_error
from developer_myself.shared.logging import log

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def current_admin(request: Request, learner_id: LearnerIdDep) -> UserId:
    """Confere a cada chamada: tirar o e-mail de `DM_ADMIN_EMAILS` corta o acesso na hora."""
    admin_id = UserId(learner_id)
    await request.app.state.container.identity.require_admin(admin_id)
    return admin_id


AdminDep = Annotated[UserId, Depends(current_admin)]


class AccountOut(BaseModel):
    id: uuid.UUID
    email: str
    username: str | None
    created_at: datetime
    last_activity_at: datetime | None
    contents: int
    sessions: int


class AccountsPageOut(BaseModel):
    items: list[AccountOut]
    next_cursor: str | None


class RegistrationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    open: StrictBool


class RegistrationOut(BaseModel):
    open: bool


async def _overviews(request: Request, users: list[User]) -> list[AccountOut]:
    """Busca contagens e última sessão em lote (2 queries por página, sem N+1)."""
    if not users:
        return []
    container = request.app.state.container
    ids = [u.id.value for u in users]
    content_counts = await container.learning.content_counts(ids)
    summaries = await container.history.store.summaries_for([str(i) for i in ids])
    out: list[AccountOut] = []
    for user in users:
        learner = user.id.value
        summary = summaries.get(str(learner))
        out.append(
            AccountOut(
                id=learner,
                email=user.email.value,
                username=user.username.value if user.username else None,
                created_at=user.created_at,
                last_activity_at=summary.last_activity_at if summary else None,
                contents=content_counts.get(learner, 0),
                sessions=summary.sessions if summary else 0,
            )
        )
    return out


def _decode_user_cursor(token: str) -> UserCursor:
    moment, raw_id = decode_cursor(token)
    try:
        return UserCursor(moment, uuid.UUID(raw_id))
    except ValueError as exc:
        raise http_error(422, "Cursor de paginação inválido.", "INVALID_CURSOR") from exc


@router.get("/accounts")
async def list_accounts(
    request: Request,
    admin_id: AdminDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> AccountsPageOut:
    identity = request.app.state.container.identity
    after = _decode_user_cursor(cursor) if cursor else None
    page = await identity.list_accounts(admin_id, limit, after)
    return AccountsPageOut(
        items=await _overviews(request, page.items),
        next_cursor=(
            encode_cursor(page.next.created_at, str(page.next.user_id)) if page.next else None
        ),
    )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(request: Request, admin_id: AdminDep, account_id: uuid.UUID) -> None:
    container = request.app.state.container
    try:
        await container.identity.admin_delete(admin_id, UserId(account_id))
    except UserNotFoundError:
        # Uma tentativa anterior pode ter apagado a conta e falhado na limpeza: o erase é
        # idempotente, então repetir a exclusão termina o serviço (LGPD) e ainda responde 404.
        await container.erase_learner_data(account_id)
        raise
    await container.erase_learner_data(account_id)
    # Auditoria sem dado pessoal (só ids), em warning: não some com DM_LOG_LEVEL=WARNING.
    log.warning("admin_deleted_account", admin_id=str(admin_id.value), account_id=str(account_id))


@router.get("/registration")
async def get_registration(request: Request, _: AdminDep) -> RegistrationOut:
    return RegistrationOut(open=await request.app.state.container.identity.registration_open())


@router.put("/registration")
async def set_registration(
    request: Request, admin_id: AdminDep, body: RegistrationIn
) -> RegistrationOut:
    identity = request.app.state.container.identity
    await identity.set_registration(admin_id, body.open)
    log.warning("admin_set_registration", admin_id=str(admin_id.value), open=body.open)
    return RegistrationOut(open=await identity.registration_open())
