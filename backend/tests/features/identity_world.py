"""Mundo dos cenários de identidade (admin, username): casos de uso em memória."""

import asyncio
from collections.abc import Coroutine, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from developer_myself.identity.adapters.memory.repositories import (
    InMemoryAuthSessionRepository,
    InMemoryRegistrationGate,
    InMemoryUserRepository,
    PlainTextHasherForTests,
)
from developer_myself.identity.application.use_cases import IdentityUseCases, UserPage
from developer_myself.identity.domain.model import Email, IdentityError, User, UserId
from developer_myself.shared.clock import FakeClock

PASSWORD = "senha-forte-123"  # gitleaks:allow


@dataclass
class IdentityWorld:
    runner: asyncio.Runner
    clock: FakeClock = field(default_factory=FakeClock)
    users: InMemoryUserRepository = field(default_factory=InMemoryUserRepository)
    gate: InMemoryRegistrationGate = field(default_factory=InMemoryRegistrationGate)
    admin_emails: frozenset[Email] = frozenset()
    error: IdentityError | None = None
    page: UserPage | None = None
    page_size: int = 0
    filled: int = 0
    logged_in: bool = False
    # Excluídos continuam endereçáveis pelo e-mail nos passos seguintes.
    ids: dict[str, UserId] = field(default_factory=dict)

    @property
    def uc(self) -> IdentityUseCases:
        return IdentityUseCases(
            self.users,
            InMemoryAuthSessionRepository(),
            PlainTextHasherForTests(),
            self.clock,
            registration=self.gate,
            admin_emails=self.admin_emails,
        )

    def run[T](self, coro: Coroutine[Any, Any, T]) -> T:
        return self.runner.run(coro)

    def user(self, email: str) -> User:
        found = self.run(self.users.get_by_email(Email(email)))
        assert found is not None, f"{email} não está cadastrado"
        self.ids[email] = found.id
        return found

    def id_of(self, email: str) -> UserId:
        return self.ids.get(email) or self.user(email).id

    def attempt(self, coro: Coroutine[Any, Any, object]) -> None:
        try:
            self.run(coro)
        except IdentityError as exc:
            self.error = exc


@pytest.fixture
def admin() -> Iterator[IdentityWorld]:
    with asyncio.Runner() as runner:
        yield IdentityWorld(runner)
