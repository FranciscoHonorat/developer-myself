"""Migração de usernames com duas instâncias subindo juntas (deploy sobreposto)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from developer_myself.identity.adapters.memory.repositories import (
    InMemoryAuthSessionRepository,
    InMemoryUserRepository,
    PlainTextHasherForTests,
)
from developer_myself.identity.application.use_cases import IdentityUseCases
from developer_myself.identity.domain.model import Email, InvalidCredentialsError, User, UserId
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


class CountingUserRepository(InMemoryUserRepository):
    scans: int = 0

    async def without_username(self) -> list[User]:
        self.scans += 1
        return await super().without_username()


def test_unknown_logins_do_not_rescan_legacy_users_repeatedly() -> None:
    users = CountingUserRepository()
    clock = FakeClock()
    use_cases = IdentityUseCases(
        users, InMemoryAuthSessionRepository(), PlainTextHasherForTests(), clock
    )

    async def attempt() -> None:
        with pytest.raises(InvalidCredentialsError):
            await use_cases.login("inexistente", "senha-forte-123")

    for _ in range(5):
        asyncio.run(attempt())
    assert users.scans == 1

    clock.advance(minutes=6)
    asyncio.run(attempt())
    assert users.scans == 2
