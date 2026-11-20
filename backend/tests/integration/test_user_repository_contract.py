"""Contrato da listagem de contas do admin: memória e Mongo paginam igual (ADR-0003)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker

from developer_myself.identity.adapters.memory.repositories import InMemoryUserRepository
from developer_myself.identity.adapters.mongo.repositories import MongoUserRepository
from developer_myself.identity.application.ports import UserRepository
from developer_myself.identity.domain.model import Email, User, UserCursor, UserId
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


def user(n: int, minutes: int) -> User:
    # ids crescentes: uuid com o número no fim deixa o desempate previsível.
    return User(
        UserId(uuid.UUID(int=n)),
        Email(f"u{n}@exemplo.com"),
        "hash",
        NOW + timedelta(minutes=minutes),
    )


@pytest.fixture(
    params=["memory", pytest.param("mongo", marks=[pytest.mark.integration, requires_docker])]
)
async def users(request: pytest.FixtureRequest) -> AsyncIterator[UserRepository]:
    if request.param == "memory":
        yield InMemoryUserRepository()
        return
    url: str = request.getfixturevalue("mongo_url")
    client = make_client(url)
    name = f"contract_users_{uuid.uuid4().hex[:12]}"
    db: AsyncDatabase[Doc] = client[name]
    await ensure_schema(db)
    yield MongoUserRepository(db.users)
    await client.drop_database(name)
    await client.close()


async def test_pages_newest_first_and_ties_by_id(users: UserRepository) -> None:
    # u2 e u3 se cadastraram no mesmo instante: o id decide, sem pular nem repetir.
    for u in (user(1, 0), user(2, 10), user(3, 10), user(4, 20)):
        await users.add(u)
    first = await users.page(2)
    assert [u.email.value for u in first] == ["u4@exemplo.com", "u3@exemplo.com"]
    second = await users.page(2, UserCursor.of(first[-1]))
    assert [u.email.value for u in second] == ["u2@exemplo.com", "u1@exemplo.com"]
    assert await users.page(2, UserCursor.of(second[-1])) == []


async def test_page_keeps_created_at_in_utc(users: UserRepository) -> None:
    await users.add(user(1, 0))
    [found] = await users.page(5)
    assert found.created_at == NOW
