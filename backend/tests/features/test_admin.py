"""Steps do perfil de admin, sobre `IdentityUseCases` com repositórios em memória."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from tests.features.identity_world import PASSWORD, IdentityWorld

from developer_myself.identity.domain.model import (
    CannotDeleteSelfError,
    Email,
    InvalidCredentialsError,
    NotAdminError,
    RegistrationClosedError,
    UserNotFoundError,
    parse_admin_emails,
    username_from_email,
)

scenarios("admin.feature")


def handle(email: str) -> str:
    """Username dos cenários de admin: derivado do e-mail, como nas contas antigas."""
    return username_from_email(Email(email), lambda _: False).value


@given(parsers.parse('que os admins configurados são "{raw}"'))
def given_admins(admin: IdentityWorld, raw: str) -> None:
    admin.admin_emails = parse_admin_emails(raw)


@given(parsers.parse('que "{email}" se cadastrou'))
@when(parsers.parse('"{email}" se cadastra'))
def register(admin: IdentityWorld, email: str) -> None:
    admin.clock.advance(minutes=1)
    admin.run(admin.uc.register(handle(email), email, PASSWORD))
    admin.user(email)


@when(parsers.parse('"{email}" tenta se cadastrar'))
def try_register(admin: IdentityWorld, email: str) -> None:
    admin.attempt(admin.uc.register(handle(email), email, PASSWORD))


@given("que o cadastro está fechado")
def given_closed(admin: IdentityWorld) -> None:
    admin.run(admin.gate.set_open(False))


@when(parsers.parse('"{email}" fecha o cadastro'))
def close(admin: IdentityWorld, email: str) -> None:
    admin.run(admin.uc.set_registration(admin.user(email).id, open=False))


@when(parsers.parse('"{email}" abre o cadastro'))
def reopen(admin: IdentityWorld, email: str) -> None:
    admin.run(admin.uc.set_registration(admin.user(email).id, open=True))


@when(parsers.parse('"{email}" tenta fechar o cadastro'))
def try_close(admin: IdentityWorld, email: str) -> None:
    admin.attempt(admin.uc.set_registration(admin.user(email).id, open=False))


@then(parsers.parse('"{email}" é admin'))
def is_admin(admin: IdentityWorld, email: str) -> None:
    assert admin.run(admin.uc.is_admin(admin.user(email).id))


@then(parsers.parse('"{email}" não é admin'))
def is_not_admin(admin: IdentityWorld, email: str) -> None:
    assert not admin.run(admin.uc.is_admin(admin.user(email).id))


@then("a ação é recusada porque o cadastro está fechado")
def refused_closed(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, RegistrationClosedError)


@then("a ação é recusada por falta de permissão")
def refused_forbidden(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, NotAdminError)


@then("o cadastro está aberto")
def is_open(admin: IdentityWorld) -> None:
    assert admin.run(admin.uc.registration_open())


@when(parsers.parse('"{email}" lista as contas com {size:d} por página'))
def list_accounts(admin: IdentityWorld, email: str, size: int) -> None:
    admin.page_size = size
    admin.page = admin.run(admin.uc.list_accounts(admin.id_of(email), size))


@when(parsers.parse('"{email}" abre a próxima página de contas'))
def next_accounts(admin: IdentityWorld, email: str) -> None:
    assert admin.page is not None
    assert admin.page.next is not None
    admin.page = admin.run(
        admin.uc.list_accounts(admin.id_of(email), admin.page_size, after=admin.page.next)
    )


@when(parsers.parse('"{email}" tenta listar as contas'))
def try_list(admin: IdentityWorld, email: str) -> None:
    admin.attempt(admin.uc.list_accounts(admin.id_of(email), 10))


@given(parsers.parse('que "{actor}" excluiu a conta de "{target}"'))
@when(parsers.parse('"{actor}" exclui a conta de "{target}"'))
def delete_account(admin: IdentityWorld, actor: str, target: str) -> None:
    admin.run(admin.uc.admin_delete(admin.id_of(actor), admin.id_of(target)))


@when(parsers.re(r'"(?P<actor>[^"]+)" tenta excluir a conta de "(?P<target>[^"]+)"( de novo)?'))
def try_delete(admin: IdentityWorld, actor: str, target: str) -> None:
    admin.attempt(admin.uc.admin_delete(admin.id_of(actor), admin.id_of(target)))


@then(parsers.parse("vê as contas {emails}"))
def sees(admin: IdentityWorld, emails: str) -> None:
    assert admin.page is not None
    expected = [e.strip().strip('"') for e in emails.split(",")]
    assert [u.email.value for u in admin.page.items] == expected


@then("existe outra página de contas")
def has_next(admin: IdentityWorld) -> None:
    assert admin.page is not None
    assert admin.page.next is not None


@then("não existe outra página de contas")
def no_next(admin: IdentityWorld) -> None:
    assert admin.page is not None
    assert admin.page.next is None


@then(parsers.parse('"{email}" não consegue mais entrar'))
def cannot_login(admin: IdentityWorld, email: str) -> None:
    with pytest.raises(InvalidCredentialsError):
        admin.run(admin.uc.login(handle(email), PASSWORD))


@then("a ação é recusada porque não se exclui a própria conta por aqui")
def refused_self(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, CannotDeleteSelfError)


@then("a ação é recusada porque a conta não existe")
def refused_missing(admin: IdentityWorld) -> None:
    assert isinstance(admin.error, UserNotFoundError)
