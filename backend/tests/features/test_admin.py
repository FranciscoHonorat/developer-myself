"""Steps do perfil de admin, sobre `IdentityUseCases` com repositórios em memória."""

import asyncio
from collections.abc import Coroutine, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from developer_myself.identity.adapters.memory.repositories import (
    InMemoryAuthSessionRepository,
    InMemoryRegistrationGate,
    InMemoryUserRepository,
    PlainTextHasherForTests,
)
from developer_myself.identity.application.use_cases import IdentityUseCases, UserPage
from developer_myself.identity.domain.model import (
    CannotDeleteSelfError,
    Email,
    IdentityError,
    InvalidCredentialsError,
    NotAdminError,
    RegistrationClosedError,
    User,
    UserId,
    UserNotFoundError,
    parse_admin_emails,
)
from developer_myself.shared.clock import FakeClock

scenarios("admin.feature")
PASSWORD = "senha-forte-123"  # gitleaks:allow


@dataclass
class Admin:
    runner: asyncio.Runner
    clock: FakeClock = field(default_factory=FakeClock)
    users: InMemoryUserRepository = field(default_factory=InMemoryUserRepository)
    gate: InMemoryRegistrationGate = field(default_factory=InMemoryRegistrationGate)
    admin_emails: frozenset[Email] = frozenset()
    error: IdentityError | None = None
    page: UserPage | None = None
    page_size: int = 0
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
def admin() -> Iterator[Admin]:
    with asyncio.Runner() as runner:
        yield Admin(runner)


@given(parsers.parse('que os admins configurados são "{raw}"'))
def given_admins(admin: Admin, raw: str) -> None:
    admin.admin_emails = parse_admin_emails(raw)


@given(parsers.parse('que "{email}" se cadastrou'))
@when(parsers.parse('"{email}" se cadastra'))
def register(admin: Admin, email: str) -> None:
    admin.clock.advance(minutes=1)
    admin.run(admin.uc.register(email, PASSWORD))
    admin.user(email)


@when(parsers.parse('"{email}" tenta se cadastrar'))
def try_register(admin: Admin, email: str) -> None:
    admin.attempt(admin.uc.register(email, PASSWORD))


@given("que o cadastro está fechado")
def given_closed(admin: Admin) -> None:
    admin.run(admin.gate.set_open(False))


@when(parsers.parse('"{email}" fecha o cadastro'))
def close(admin: Admin, email: str) -> None:
    admin.run(admin.uc.set_registration(admin.user(email).id, open=False))


@when(parsers.parse('"{email}" abre o cadastro'))
def reopen(admin: Admin, email: str) -> None:
    admin.run(admin.uc.set_registration(admin.user(email).id, open=True))


@when(parsers.parse('"{email}" tenta fechar o cadastro'))
def try_close(admin: Admin, email: str) -> None:
    admin.attempt(admin.uc.set_registration(admin.user(email).id, open=False))


@then(parsers.parse('"{email}" é admin'))
def is_admin(admin: Admin, email: str) -> None:
    assert admin.run(admin.uc.is_admin(admin.user(email).id))


@then(parsers.parse('"{email}" não é admin'))
def is_not_admin(admin: Admin, email: str) -> None:
    assert not admin.run(admin.uc.is_admin(admin.user(email).id))


@then("a ação é recusada porque o cadastro está fechado")
def refused_closed(admin: Admin) -> None:
    assert isinstance(admin.error, RegistrationClosedError)


@then("a ação é recusada por falta de permissão")
def refused_forbidden(admin: Admin) -> None:
    assert isinstance(admin.error, NotAdminError)


@then("o cadastro está aberto")
def is_open(admin: Admin) -> None:
    assert admin.run(admin.uc.registration_open())


@when(parsers.parse('"{email}" lista as contas com {size:d} por página'))
def list_accounts(admin: Admin, email: str, size: int) -> None:
    admin.page_size = size
    admin.page = admin.run(admin.uc.list_accounts(admin.id_of(email), size))


@when(parsers.parse('"{email}" abre a próxima página de contas'))
def next_accounts(admin: Admin, email: str) -> None:
    assert admin.page is not None
    assert admin.page.next is not None
    admin.page = admin.run(
        admin.uc.list_accounts(admin.id_of(email), admin.page_size, after=admin.page.next)
    )


@when(parsers.parse('"{email}" tenta listar as contas'))
def try_list(admin: Admin, email: str) -> None:
    admin.attempt(admin.uc.list_accounts(admin.id_of(email), 10))


@given(parsers.parse('que "{actor}" excluiu a conta de "{target}"'))
@when(parsers.parse('"{actor}" exclui a conta de "{target}"'))
def delete_account(admin: Admin, actor: str, target: str) -> None:
    admin.run(admin.uc.admin_delete(admin.id_of(actor), admin.id_of(target)))


@when(parsers.re(r'"(?P<actor>[^"]+)" tenta excluir a conta de "(?P<target>[^"]+)"( de novo)?'))
def try_delete(admin: Admin, actor: str, target: str) -> None:
    admin.attempt(admin.uc.admin_delete(admin.id_of(actor), admin.id_of(target)))


@then(parsers.parse("vê as contas {emails}"))
def sees(admin: Admin, emails: str) -> None:
    assert admin.page is not None
    expected = [e.strip().strip('"') for e in emails.split(",")]
    assert [u.email.value for u in admin.page.items] == expected


@then("existe outra página de contas")
def has_next(admin: Admin) -> None:
    assert admin.page is not None
    assert admin.page.next is not None


@then("não existe outra página de contas")
def no_next(admin: Admin) -> None:
    assert admin.page is not None
    assert admin.page.next is None


@then(parsers.parse('"{email}" não consegue mais entrar'))
def cannot_login(admin: Admin, email: str) -> None:
    with pytest.raises(InvalidCredentialsError):
        admin.run(admin.uc.login(email, PASSWORD))


@then("a ação é recusada porque não se exclui a própria conta por aqui")
def refused_self(admin: Admin) -> None:
    assert isinstance(admin.error, CannotDeleteSelfError)


@then("a ação é recusada porque a conta não existe")
def refused_missing(admin: Admin) -> None:
    assert isinstance(admin.error, UserNotFoundError)
