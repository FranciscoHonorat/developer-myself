"""Área de admin (`/api/admin/*`): permissão, listagem, exclusão e cadastro."""

import asyncio
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from developer_myself.bootstrap import build_memory_container, create_app
from developer_myself.identity.adapters.memory.repositories import PlainTextHasherForTests
from developer_myself.identity.domain.model import parse_admin_emails
from developer_myself.learning.domain.errors import StudyPlanNotFoundError
from developer_myself.shared.clock import FakeClock
from developer_myself.shared.settings import Settings

H = {"X-Requested-With": "fetch"}
PASSWORD = "senha-forte-123"  # gitleaks:allow
ADMIN = "admin@exemplo.com"
NOTES = {
    "studied": "Capítulo sobre funções pequenas e nomes",
    "understood": "Uma função deve fazer uma coisa só",
    "to_review": "Separação comando/consulta",
}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock) -> Iterator[TestClient]:
    settings = Settings(
        storage="memory",
        cookie_secure=False,
        log_json=False,
        log_level="WARNING",
        admin_emails=ADMIN,
    )
    container = build_memory_container(settings, clock=clock, hasher=PlainTextHasherForTests())
    with TestClient(create_app(settings, container)) as c:
        yield c


def register(client: TestClient, email: str, clock: FakeClock | None = None) -> dict[str, Any]:
    if clock is not None:
        clock.advance(minutes=1)  # created_at distintos: ordem previsível na listagem
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "timezone": "America/Sao_Paulo"},
        headers=H,
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def login(client: TestClient, email: str) -> None:
    client.post("/api/auth/logout", headers=H)
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}, headers=H)
    assert r.status_code == 204, r.text


def accounts(client: TestClient, **params: Any) -> dict[str, Any]:
    r = client.get("/api/admin/accounts", params=params)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


ADMIN_CALLS = [
    ("GET", "/api/admin/accounts", None),
    ("DELETE", "/api/admin/accounts/0190a000-0000-7000-8000-000000000000", None),
    ("GET", "/api/admin/registration", None),
    ("PUT", "/api/admin/registration", {"open": False}),
]


def call(client: TestClient, method: str, path: str, body: Any) -> Any:
    return client.request(method, path, json=body, headers=H)


def test_me_reports_is_admin(client: TestClient) -> None:
    register(client, "outra@exemplo.com")
    assert client.get("/api/auth/me").json()["is_admin"] is False
    register(client, ADMIN)
    assert client.get("/api/auth/me").json()["is_admin"] is True


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_CALLS)
def test_admin_routes_require_login(client: TestClient, method: str, path: str, body: Any) -> None:
    assert call(client, method, path, body).status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), ADMIN_CALLS)
def test_admin_routes_forbid_non_admin(
    client: TestClient, method: str, path: str, body: Any
) -> None:
    register(client, "outra@exemplo.com")
    r = call(client, method, path, body)
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


def test_list_accounts_shows_counts_not_notes(client: TestClient, clock: FakeClock) -> None:
    register(client, "aluno@exemplo.com", clock)
    content = client.post(
        "/api/contents", json={"title": "Clean Code", "kind": "BOOK"}, headers=H
    ).json()
    client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    clock.advance(minutes=25)
    client.post("/api/sessions/current/finish", json=NOTES, headers=H)
    register(client, ADMIN, clock)

    r = client.get("/api/admin/accounts")
    aluno = next(a for a in r.json()["items"] if a["email"] == "aluno@exemplo.com")
    assert aluno["contents"] == 1
    assert aluno["sessions"] == 1
    assert aluno["last_activity_at"] is not None
    assert set(aluno) == {"id", "email", "created_at", "last_activity_at", "contents", "sessions"}
    for text in NOTES.values():
        assert text not in r.text


def test_list_accounts_paginates(client: TestClient, clock: FakeClock) -> None:
    register(client, "a@exemplo.com", clock)
    register(client, "b@exemplo.com", clock)
    register(client, ADMIN, clock)
    first = accounts(client, limit=2)
    assert [a["email"] for a in first["items"]] == [ADMIN, "b@exemplo.com"]
    second = accounts(client, limit=2, cursor=first["next_cursor"])
    assert [a["email"] for a in second["items"]] == ["a@exemplo.com"]
    assert second["next_cursor"] is None


@pytest.mark.parametrize("cursor", ["lixo", "e30", "eyJ0IjoiMjAyNiJ9"])
def test_list_accounts_rejects_bad_cursor(client: TestClient, cursor: str) -> None:
    register(client, ADMIN)
    r = client.get("/api/admin/accounts", params={"cursor": cursor})
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_CURSOR"


def test_account_without_plan_lists_zero_contents(client: TestClient) -> None:
    # Cadastro interrompido: existe o usuário, mas a trilha não foi criada.
    container = client.app.state.container  # type: ignore[attr-defined]
    asyncio.run(container.identity.register("sem-trilha@exemplo.com", PASSWORD))
    register(client, ADMIN)
    item = next(a for a in accounts(client)["items"] if a["email"] == "sem-trilha@exemplo.com")
    assert item["contents"] == 0
    assert item["sessions"] == 0
    assert item["last_activity_at"] is None


def test_admin_deletes_account_and_its_data(client: TestClient, clock: FakeClock) -> None:
    target = register(client, "aluno@exemplo.com", clock)
    client.post("/api/contents", json={"title": "Clean Code", "kind": "BOOK"}, headers=H)
    register(client, ADMIN, clock)

    assert client.delete(f"/api/admin/accounts/{target['id']}", headers=H).status_code == 204
    assert [a["email"] for a in accounts(client)["items"]] == [ADMIN]
    client.post("/api/auth/logout", headers=H)
    r = client.post(
        "/api/auth/login", json={"email": "aluno@exemplo.com", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 401
    # Os dados de estudo também se foram: recadastrar começa com a trilha vazia.
    register(client, "aluno@exemplo.com", clock)
    assert client.get("/api/plan").json()["contents"] == []


def test_admin_cannot_delete_self(client: TestClient) -> None:
    me = register(client, ADMIN)
    r = client.delete(f"/api/admin/accounts/{me['id']}", headers=H)
    assert r.status_code == 409
    assert r.json()["code"] == "CANNOT_DELETE_SELF"


def test_delete_unknown_account(client: TestClient) -> None:
    register(client, ADMIN)
    r = client.delete("/api/admin/accounts/0190a000-0000-7000-8000-000000000000", headers=H)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_closed_registration_blocks_new_accounts_but_not_admin(client: TestClient) -> None:
    register(client, ADMIN)
    r = client.put("/api/admin/registration", json={"open": False}, headers=H)
    assert r.json() == {"open": False}
    assert client.get("/api/admin/registration").json() == {"open": False}
    client.post("/api/auth/logout", headers=H)

    blocked = client.post(
        "/api/auth/register",
        json={"email": "nova@exemplo.com", "password": PASSWORD, "timezone": "America/Sao_Paulo"},
        headers=H,
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "REGISTRATION_CLOSED"


def test_public_registration_status(client: TestClient) -> None:
    assert client.get("/api/auth/registration").json() == {"open": True}


def test_admin_losing_status_gets_403(client: TestClient) -> None:
    register(client, ADMIN)
    assert client.get("/api/admin/accounts").status_code == 200
    container = client.app.state.container  # type: ignore[attr-defined]
    container.identity.admin_emails = parse_admin_emails("")
    assert client.get("/api/admin/accounts").status_code == 403


def test_admin_delete_is_audited_without_email(client: TestClient, clock: FakeClock) -> None:
    target = register(client, "aluno@exemplo.com", clock)
    me = register(client, ADMIN, clock)
    with capture_logs() as logs:
        client.delete(f"/api/admin/accounts/{target['id']}", headers=H)
    [audit] = [e for e in logs if e["event"] == "admin_deleted_account"]
    assert audit["admin_id"] == me["id"]
    assert audit["account_id"] == target["id"]
    assert "aluno@exemplo.com" not in str(audit)


def test_closed_registration_does_not_reveal_existing_admin_email(client: TestClient) -> None:
    """Fechado, um e-mail de admin já cadastrado recebe o mesmo 403 de qualquer outro."""
    register(client, ADMIN)
    client.put("/api/admin/registration", json={"open": False}, headers=H)
    client.post("/api/auth/logout", headers=H)
    r = client.post(
        "/api/auth/register",
        json={"email": ADMIN, "password": PASSWORD, "timezone": "America/Sao_Paulo"},
        headers=H,
    )
    assert r.status_code == 403
    assert r.json()["code"] == "REGISTRATION_CLOSED"


def test_boot_warns_about_admin_emails_without_account(clock: FakeClock) -> None:
    """Admin sem conta pode ser tomado por quem se cadastrar primeiro: avisar no boot."""
    settings = Settings(
        storage="memory",
        cookie_secure=False,
        log_json=False,
        log_level="WARNING",
        admin_emails=f"{ADMIN},outro-admin@exemplo.com",
    )
    container = build_memory_container(settings, clock=clock, hasher=PlainTextHasherForTests())
    asyncio.run(container.identity.register(ADMIN, PASSWORD))
    app = create_app(settings, container)  # configura o log; capturar só depois
    with capture_logs() as logs, TestClient(app):
        pass
    [warning] = [e for e in logs if e["event"] == "admin_email_without_account"]
    assert warning["count"] == 1
    assert "outro-admin" not in str(warning)


def test_retry_after_failed_erase_still_removes_study_data(
    client: TestClient, clock: FakeClock
) -> None:
    """Se a limpeza falhar no meio, tentar de novo apaga trilha/histórico/caderno (LGPD)."""
    target = register(client, "aluno@exemplo.com", clock)
    client.post("/api/contents", json={"title": "Clean Code", "kind": "BOOK"}, headers=H)
    register(client, ADMIN, clock)
    container = client.app.state.container  # type: ignore[attr-defined]
    real_erase = container.erase_learner_data

    async def flaky_erase(_: Any) -> None:
        raise ConnectionError("Mongo caiu no meio")

    container.erase_learner_data = flaky_erase
    with pytest.raises(ConnectionError):
        client.delete(f"/api/admin/accounts/{target['id']}", headers=H)
    container.erase_learner_data = real_erase

    retry = client.delete(f"/api/admin/accounts/{target['id']}", headers=H)
    assert retry.status_code in {204, 404}
    with pytest.raises(StudyPlanNotFoundError):
        asyncio.run(container.learning.get_plan(uuid.UUID(target["id"])))
