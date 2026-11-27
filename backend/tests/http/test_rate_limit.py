"""Rate limit global da API (ADR-0009): 429 + Retry-After, separado por tipo de rota."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from developer_myself.composition.container import build_memory_container, create_app
from developer_myself.identity.adapters.memory.repositories import PlainTextHasherForTests
from developer_myself.shared.clock import FakeClock
from developer_myself.shared.settings import Settings

H = {"X-Requested-With": "fetch"}
PASSWORD = "senha-forte-123"  # gitleaks:allow


def make_client(**limits: int) -> TestClient:
    settings = Settings(
        storage="memory", cookie_secure=False, log_json=False, log_level="WARNING"
    ).model_copy(update=limits)
    container = build_memory_container(
        settings, clock=FakeClock(), hasher=PlainTextHasherForTests()
    )
    return TestClient(create_app(settings, container))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client(rate_limit_reads_per_minute=3, rate_limit_writes_per_minute=2) as c:
        yield c


def test_reads_over_the_limit_get_429_with_retry_after(client: TestClient) -> None:
    statuses = [client.get("/api/plan").status_code for _ in range(4)]
    assert statuses == [401, 401, 401, 429]
    blocked = client.get("/api/plan")
    assert blocked.json()["code"] == "RATE_LIMIT"
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    assert blocked.headers["x-correlation-id"]  # passou pelo middleware de contexto


def test_writes_have_their_own_smaller_budget(client: TestClient) -> None:
    writes = [client.put("/api/queue", json={}, headers=H).status_code for _ in range(3)]
    assert writes[-1] == 429
    assert client.get("/api/plan").status_code == 401  # leitura ainda tem cota


def test_health_checks_and_static_files_are_not_limited(client: TestClient) -> None:
    assert all(client.get("/healthz").status_code == 200 for _ in range(10))


def test_register_is_limited_per_hour() -> None:
    with make_client(rate_limit_registers_per_hour=1) as c:
        body = {
            "username": "aaa",
            "email": "a@exemplo.com",
            "password": PASSWORD,
            "timezone": "America/Sao_Paulo",
        }
        assert c.post("/api/auth/register", json=body, headers=H).status_code == 201
        body |= {"username": "bbb", "email": "b@exemplo.com"}
        r = c.post("/api/auth/register", json=body, headers=H)
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) > 60


def test_export_is_limited() -> None:
    with make_client(rate_limit_exports_per_minute=1) as c:
        assert c.get("/api/export").status_code == 401
        assert c.get("/api/export").status_code == 429


def test_limit_zero_disables_it() -> None:
    with make_client(rate_limit_reads_per_minute=0) as c:
        assert all(c.get("/api/plan").status_code == 401 for _ in range(20))


def test_sensitive_auth_routes_have_strict_rate_limit() -> None:
    with make_client(rate_limit_sensitive_per_minute=2, rate_limit_writes_per_minute=100) as c:
        statuses = [
            c.put(
                "/api/auth/username", json={"username": "novo", "password": PASSWORD}, headers=H
            ).status_code
            for _ in range(3)
        ]
        assert statuses == [401, 401, 429]
        # Delete-account divide o mesmo orçamento sensível
        assert (
            c.post("/api/auth/delete-account", json={"password": PASSWORD}, headers=H).status_code
            == 429
        )
