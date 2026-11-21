"""Steps do username: migração de contas antigas, cadastro, login e troca."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.identity_world import PASSWORD, IdentityWorld

from developer_myself.identity.domain.model import (
    Email,
    InvalidCredentialsError,
    User,
    UserId,
    Username,
    UsernameTakenError,
)

scenarios("username.feature")


def rows(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *body = datatable
    return [dict(zip(header, row, strict=True)) for row in body]


@given(parsers.parse("as contas antigas sem username, da mais antiga para a mais nova:"))
def given_legacy(admin: IdentityWorld, datatable: list[list[str]]) -> None:
    for row in rows(datatable):
        admin.clock.advance(minutes=1)
        legacy = User(UserId.new(), Email(row["email"]), "plain$x", admin.clock.now())
        admin.run(admin.users.add(legacy))


@given("que os usernames que faltam foram preenchidos")
@when("os usernames que faltam são preenchidos")
def fill(admin: IdentityWorld) -> None:
    admin.filled = admin.run(admin.uc.assign_missing_usernames())


@then(parsers.parse("{count:d} contas ganham username"))
def filled_count(admin: IdentityWorld, count: int) -> None:
    assert admin.filled == count


@then("os usernames são:")
def usernames(admin: IdentityWorld, datatable: list[list[str]]) -> None:
    for row in rows(datatable):
        user = admin.user(row["email"])
        assert user.username is not None
        assert user.username.value == row["username"]


def user_by_username(admin: IdentityWorld, username: str) -> User:
    found = admin.run(admin.users.get_by_username(Username(username)))
    assert found is not None
    return found


@given(parsers.parse('que "{username}" se cadastrou com o e-mail "{email}"'))
def given_registered(admin: IdentityWorld, username: str, email: str) -> None:
    admin.run(admin.uc.register(username, email, PASSWORD))


@when(parsers.parse('"{username}" tenta se cadastrar com o e-mail "{email}"'))
def try_register(admin: IdentityWorld, username: str, email: str) -> None:
    admin.attempt(admin.uc.register(username, email, PASSWORD))


@when(parsers.parse('"{username}" entra com a senha certa'))
@then(parsers.parse('"{username}" entra com a senha certa'))
def login(admin: IdentityWorld, username: str) -> None:
    admin.logged_in = False
    admin.attempt(admin.uc.login(username, PASSWORD))
    admin.logged_in = admin.error is None


@when(parsers.parse('"{username}" troca o username para "{new}" com a senha certa'))
def change(admin: IdentityWorld, username: str, new: str) -> None:
    admin.run(admin.uc.change_username(user_by_username(admin, username).id, new, PASSWORD))


@when(parsers.parse('"{username}" tenta trocar o username para "{new}" com a senha errada'))
def change_wrong(admin: IdentityWorld, username: str, new: str) -> None:
    user_id = user_by_username(admin, username).id
    admin.attempt(admin.uc.change_username(user_id, new, "senha-errada-123"))


@then("o login funciona")
def login_ok(admin: IdentityWorld) -> None:
    assert admin.logged_in, admin.error


@then("o login é recusado")
def login_refused(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, InvalidCredentialsError)
    assert str(admin.error) == "Username ou senha inválidos."


@then(parsers.parse('"{username}" não entra mais'))
def cannot_login(admin: IdentityWorld, username: str) -> None:
    with pytest.raises(InvalidCredentialsError):
        admin.run(admin.uc.login(username, PASSWORD))


@then("a ação é recusada porque o username está em uso")
def refused_taken(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, UsernameTakenError)
