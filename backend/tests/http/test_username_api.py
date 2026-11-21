"""Username na API: cadastro, login só por username, troca, admin e migração no boot."""

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from developer_myself.composition.container import build_memory_container, create_app
from developer_myself.identity.adapters.memory.repositories import PlainTextHasherForTests
from developer_myself.identity.domain.model import Email, User, UserId
from developer_myself.shared.clock import FakeClock
from developer_myself.shared.settings import Settings

H = {"X-Requested-With": "fetch"}
PASSWORD = "senha-forte-123"  # gitleaks:allow


def settings(**extra: Any) -> Settings:
    return Settings(
        storage="memory", cookie_secure=False, log_json=False, log_level="WARNING", **extra
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    s = settings(admin_emails="admin@exemplo.com")
    container = build_memory_container(s, clock=FakeClock(), hasher=PlainTextHasherForTests())
    with TestClient(create_app(s, container)) as c:
        yield c


def register(client: TestClient, username: str, email: str) -> Any:
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "timezone": "America/Sao_Paulo",
        },
        headers=H,
    )


def login(client: TestClient, username: str, password: str = PASSWORD) -> Any:
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}, headers=H
    )


def test_login_with_username(client: TestClient) -> None:
    assert register(client, "jose", "jose@exemplo.com").status_code == 201
    client.post("/api/auth/logout", headers=H)
    assert login(client, " Jose ").status_code == 204
    me = client.get("/api/auth/me").json()
    assert me["username"] == "jose"


def test_login_body_with_email_is_rejected(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    client.post("/api/auth/logout", headers=H)
    r = client.post(
        "/api/auth/login", json={"email": "jose@exemplo.com", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 422


def test_wrong_credentials_are_generic(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    client.post("/api/auth/logout", headers=H)
    unknown = login(client, "ninguem")
    wrong = login(client, "jose", "senha-errada-123")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"] == "Username ou senha inválidos."


def test_register_username_taken(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    client.post("/api/auth/logout", headers=H)
    r = register(client, "JOSE", "outro@exemplo.com")
    assert r.status_code == 409
    assert r.json()["code"] == "USERNAME_TAKEN"
    assert r.json()["detail"] == "Este username já está em uso."


@pytest.mark.parametrize("username", ["ab", "jo se", "josé", ""])
def test_register_invalid_username(client: TestClient, username: str) -> None:
    r = register(client, username, "jose@exemplo.com")
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_USERNAME"


def test_register_requires_username(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": "jose@exemplo.com", "password": PASSWORD},
        headers=H,
    )
    assert r.status_code == 422


def test_change_username_keeps_session(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    r = client.put(
        "/api/auth/username", json={"username": "jose.silva", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 200
    assert r.json()["username"] == "jose.silva"
    assert client.get("/api/auth/me").json()["username"] == "jose.silva"
    client.post("/api/auth/logout", headers=H)
    assert login(client, "jose").status_code == 401
    assert login(client, "jose.silva").status_code == 204


def test_change_username_wrong_password(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    r = client.put(
        "/api/auth/username", json={"username": "outro", "password": "errada-123456"}, headers=H
    )
    assert r.status_code == 401


def test_change_username_taken(client: TestClient) -> None:
    register(client, "ana", "ana@exemplo.com")
    client.post("/api/auth/logout", headers=H)
    register(client, "jose", "jose@exemplo.com")
    r = client.put("/api/auth/username", json={"username": "ana", "password": PASSWORD}, headers=H)
    assert r.status_code == 409
    assert r.json()["code"] == "USERNAME_TAKEN"


def test_login_rate_limit_keys_by_username(client: TestClient) -> None:
    register(client, "jose", "jose@exemplo.com")
    client.post("/api/auth/logout", headers=H)
    statuses = [login(client, "jose", "x").status_code for _ in range(12)]
    assert 429 in statuses


def test_admin_lists_username(client: TestClient) -> None:
    register(client, "chefe", "admin@exemplo.com")
    [item] = client.get("/api/admin/accounts").json()["items"]
    assert item["username"] == "chefe"


def test_boot_assigns_missing_usernames() -> None:
    """Conta antiga (sem username) consegue entrar logo depois do deploy."""
    s = settings()
    clock = FakeClock()
    container = build_memory_container(s, clock=clock, hasher=PlainTextHasherForTests())
    legacy = User(UserId.new(), Email("honorato@exemplo.com"), f"plain${PASSWORD}", clock.now())
    asyncio.run(container.identity.users.add(legacy))
    with TestClient(create_app(s, container)) as c:
        assert login(c, "honorato").status_code == 204
        assert c.get("/api/auth/me").json()["username"] == "honorato"


def test_account_created_by_old_instance_after_boot_can_login() -> None:
    """Deploy sobreposto: a instância antiga cria conta sem username depois da migração."""
    s = settings()
    clock = FakeClock()
    container = build_memory_container(s, clock=clock, hasher=PlainTextHasherForTests())
    with TestClient(create_app(s, container)) as c:  # boot já migrou (nada a fazer)
        late = User(UserId.new(), Email("tardio@exemplo.com"), f"plain${PASSWORD}", clock.now())
        asyncio.run(container.identity.users.add(late))
        assert login(c, "tardio").status_code == 204
