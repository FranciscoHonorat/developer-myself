"""Migração de usernames com duas instâncias subindo juntas (deploy sobreposto)."""

import asyncio
from datetime import UTC, datetime, timedelta

from developer_myself.identity.adapters.memory.repositories import (
    InMemoryAuthSessionRepository,
    InMemoryUserRepository,
    PlainTextHasherForTests,
)
from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import Email, User, UserId
from developer_myself.shared.clock import FakeClock

T0 = datetime(2026, 11, 20, 10, tzinfo=UTC)


class StaleListRepository(InMemoryUserRepository):
    """A instância B leu a lista de contas sem username ANTES de A terminar."""

    stale: list[User]

    async def without_username(self) -> list[User]:
        return self.stale


def uc(users: InMemoryUserRepository) -> IdentityUseCases:
    return IdentityUseCases(
        users, InMemoryAuthSessionRepository(), PlainTextHasherForTests(), FakeClock()
    )


def test_second_instance_with_stale_list_does_not_overwrite() -> None:
    users = StaleListRepository()
    for i, email in enumerate(["jose@a.com", "jose@b.com"]):
        asyncio.run(users.add(User(UserId.new(), Email(email), "h", T0 + timedelta(minutes=i))))
    users.stale = asyncio.run(InMemoryUserRepository.without_username(users))

    asyncio.run(uc(users).assign_missing_usernames())  # instância A
    asyncio.run(uc(users).assign_missing_usernames())  # instância B, lista velha

    current = [asyncio.run(users.get(u.id)) for u in users.stale]
    names = {u.email.value: u.username.value for u in current if u and u.username}
    assert names == {"jose@a.com": "jose", "jose@b.com": "jose-2"}
