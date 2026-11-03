"""Adapter HTTP: fino, testado à parte do BDD (ADR-0008). Tudo em memória."""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from developer_myself.bootstrap import build_memory_container, create_app
from developer_myself.identity.adapters.memory.repositories import PlainTextHasherForTests
from developer_myself.shared.clock import FakeClock
from developer_myself.shared.settings import Settings

H = {"X-Requested-With": "fetch"}
NOTES = {
    "studied": "Capítulo sobre funções pequenas e nomes",
    "understood": "Uma função deve fazer uma coisa só",
    "to_review": "Separação comando/consulta",
}
PASSWORD = "senha-forte-123"  # gitleaks:allow


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock) -> Iterator[TestClient]:
    settings = Settings(storage="memory", cookie_secure=False, log_json=False, log_level="WARNING")
    container = build_memory_container(settings, clock=clock, hasher=PlainTextHasherForTests())
    with TestClient(create_app(settings, container)) as c:
        yield c


def register(client: TestClient, email: str = "eu@exemplo.com") -> dict[str, Any]:
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "timezone": "America/Sao_Paulo"},
        headers=H,
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def add_content(client: TestClient, title: str) -> dict[str, Any]:
    r = client.post("/api/contents", json={"title": title, "kind": "BOOK"}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def consolidate(client: TestClient, clock: FakeClock, content_id: str) -> None:
    """Caminho legítimo até Intermediário: 10 sessões pontuadas + 3 desafios."""
    for _ in range(10):
        client.post("/api/sessions", json={"content_id": content_id}, headers=H)
        clock.advance(minutes=25)
        assert client.post("/api/sessions/current/finish", json=NOTES, headers=H).json()["awarded"]
    for i in range(3):
        ch = client.post(
            f"/api/contents/{content_id}/challenges",
            json={"description": f"Desafio {i}", "target_level": "INTERMEDIATE"},
            headers=H,
        ).json()
        client.post(
            f"/api/contents/{content_id}/challenges/{ch['id']}/solve",
            json={"evidence": "https://github.com/x"},
            headers=H,
        )


def test_health(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_full_session_flow(client: TestClient, clock: FakeClock) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    assert content["status"] == "IN_PROGRESS"
    assert content["next_level"] == {
        "level": "INTERMEDIATE",
        "points_required": 10,
        "challenges_required": 3,
        "challenges_solved": 0,
    }

    r = client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    assert r.json() == {"kind": "STUDY"}
    plan = client.get("/api/plan").json()
    assert plan["active_session"]["content_title"] == "Clean Code"

    clock.advance(minutes=25)
    outcome = client.post("/api/sessions/current/finish", json=NOTES, headers=H).json()
    assert outcome["awarded"] is True
    assert outcome["total_points"] == 1

    history = client.get("/api/history").json()
    assert len(history) == 1
    assert history[0]["notes_to_review"] == NOTES["to_review"]
    stats = client.get("/api/stats?days=7").json()
    assert stats["total_points"] == 1
    assert stats["current_streak_days"] == 1


def test_locked_content_and_challenges(client: TestClient) -> None:
    register(client)
    first = add_content(client, "Clean Code")
    second = add_content(client, "Refactoring")
    assert second["status"] == "LOCKED"
    assert second["queue_position"] == 1
    assert "conclua Clean Code" in second["lock_reason"]

    r = client.post("/api/sessions", json={"content_id": second["id"]}, headers=H)
    assert r.status_code == 409
    assert r.json()["code"] == "ContentLockedError"

    ch = client.post(
        f"/api/contents/{first['id']}/challenges",
        json={"description": "Refatorar um módulo", "target_level": "INTERMEDIATE"},
        headers=H,
    ).json()
    r = client.post(
        f"/api/contents/{first['id']}/challenges/{ch['id']}/solve",
        json={"evidence": "  "},
        headers=H,
    )
    assert r.status_code == 422
    r = client.post(
        f"/api/contents/{first['id']}/challenges/{ch['id']}/solve",
        json={"evidence": "https://github.com/x"},
        headers=H,
    )
    assert r.json() == {"level": "BEGINNER"}

    r = client.post(f"/api/contents/{first['id']}/finish", headers=H)
    assert r.status_code == 409
    assert r.json()["code"] == "MasteryNotReachedError"


def test_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/plan").status_code == 401


def test_csrf_header_required_on_unsafe_methods(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
    assert r.status_code == 403
    assert r.json()["code"] == "CSRF"


def test_cookie_flags(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": "eu@exemplo.com", "password": PASSWORD},
        headers=H,
    )
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie


def test_login_is_generic_and_rate_limited(client: TestClient) -> None:
    register(client)
    client.post("/api/auth/logout", headers=H)
    unknown = client.post(
        "/api/auth/login", json={"email": "nao@existe.com", "password": PASSWORD}, headers=H
    )
    wrong = client.post(
        "/api/auth/login", json={"email": "eu@exemplo.com", "password": "errada-123456"}, headers=H
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    statuses = [
        client.post(
            "/api/auth/login", json={"email": "eu@exemplo.com", "password": "x"}, headers=H
        ).status_code
        for _ in range(12)
    ]
    assert 429 in statuses


def test_nosql_injection_payload_is_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        json={"email": {"$ne": None}, "password": {"$ne": None}},
        headers=H,
    )
    assert r.status_code == 422


def test_learner_cannot_touch_other_learner(client: TestClient) -> None:
    register(client, "a@exemplo.com")
    content = add_content(client, "Clean Code")
    client.post("/api/auth/logout", headers=H)
    register(client, "b@exemplo.com")
    r = client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    assert r.status_code == 404


def test_logout_revokes_session(client: TestClient) -> None:
    register(client)
    cookie = client.cookies.get("dm_session")
    client.post("/api/auth/logout", headers=H)
    client.cookies.set("dm_session", cookie or "")
    assert client.get("/api/plan").status_code == 401


def test_export_and_delete_account(client: TestClient) -> None:
    register(client)
    add_content(client, "Clean Code")
    data = client.get("/api/export").json()
    assert data["account"]["email"] == "eu@exemplo.com"
    assert data["plan"]["contents"][0]["title"] == "Clean Code"

    r = client.post("/api/auth/delete-account", json={"password": PASSWORD}, headers=H)
    assert r.status_code == 204
    r = client.post(
        "/api/auth/login", json={"email": "eu@exemplo.com", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 401


def test_validation_errors(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register", json={"email": "invalido", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 422
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "curta"}, headers=H)
    assert r.status_code == 422
    register(client)
    r = client.post(
        "/api/auth/register", json={"email": "eu@exemplo.com", "password": PASSWORD}, headers=H
    )
    assert r.status_code == 409
    r = client.put("/api/plan/timezone", json={"timezone": "Marte/Base"}, headers=H)
    assert r.status_code == 422


def test_recommendations(client: TestClient, clock: FakeClock) -> None:
    register(client)
    data = client.get("/api/recommendations").json()
    assert data["model"] == "rede-neural"
    assert data["items"] == []
    assert data["model_info"]["trained_on"] == "synthetic"
    assert data["model_info"]["real_samples"] == 0

    content = add_content(client, "Clean Code")
    consolidate(client, clock, content["id"])
    clock.advance(days=10)
    data = client.get("/api/recommendations").json()
    assert [i["title"] for i in data["items"]] == ["Clean Code"]
    assert 0 < data["items"][0]["recall_probability"] < 1


def test_review_requires_recall_rating(client: TestClient, clock: FakeClock) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    consolidate(client, clock, content["id"])
    client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    clock.advance(minutes=25)

    r = client.post("/api/sessions/current/finish", json=NOTES, headers=H)
    assert r.status_code == 422
    assert r.json()["code"] == "RecallRatingRequiredError"

    r = client.post("/api/sessions/current/finish", json={**NOTES, "recall_rating": 7}, headers=H)
    assert r.status_code == 422

    r = client.post("/api/sessions/current/finish", json={**NOTES, "recall_rating": 3}, headers=H)
    assert r.status_code == 200
    assert r.json()["kind"] == "REVIEW"
    history = client.get("/api/history").json()
    assert history[0]["recall_rating"] == 3


def test_rename_and_remove(client: TestClient) -> None:
    register(client)
    first = add_content(client, "Clean Code")
    dup = add_content(client, "• Refactoring")  # mesma competência ("outros"): fica na fila
    r = client.patch(f"/api/contents/{dup['id']}", json={"title": "Refactoring"}, headers=H)
    assert r.status_code == 204
    titles = [c["title"] for c in client.get("/api/plan").json()["contents"]]
    assert titles == ["Clean Code", "Refactoring"]

    r = client.patch(f"/api/contents/{dup['id']}", json={"title": "clean code"}, headers=H)
    assert r.status_code == 409
    r = client.delete(f"/api/contents/{first['id']}", headers=H)
    assert r.json() == {"unlocked_content_id": dup["id"]}


def test_today_and_schedule(client: TestClient) -> None:
    register(client)
    assert client.get("/api/today").json() == {"studies": [], "reviews": [], "blocks": []}
    content = add_content(client, "Linux")
    add_content(client, "Learning Go")
    today = client.get("/api/today").json()
    assert [s["title"] for s in today["studies"]] == ["Linux", "Learning Go"]
    linux = today["studies"][0]
    assert (linux["day"], linux["total_days"]) == (1, 30)
    assert "shell e Bash" in linux["plan"]["focus"]
    assert sum(b["minutes"] for b in today["blocks"]) == 210

    sched = client.get(f"/api/contents/{content['id']}/schedule").json()
    assert sched["depth"] == "Profundo"
    assert sched["from_map"] is True
    assert sched["current_day"] == 1
    assert len(sched["days"]) == 30
    assert [d["day"] for d in sched["days"] if d["target_level"] == "INTERMEDIATE"] == [8, 9, 10]
    assert not any(d["done"] for d in sched["days"])

    r = client.get(f"/api/contents/{uuid.uuid4()}/schedule")
    assert r.status_code == 404


def test_competencies(client: TestClient, clock: FakeClock) -> None:
    register(client)
    assert client.get("/api/competencies").json()["competencies"] == []
    content = add_content(client, "Learning Go")
    consolidate(client, clock, content["id"])
    sheet = client.get("/api/competencies").json()
    go = next(c for c in sheet["competencies"] if c["key"] == "go")
    assert go["target"] == "Especialista"
    assert go["target_score"] == 75
    assert go["status"] == "em dia"
    assert go["points"] == 10
    assert sheet["xp"] == 10 * 10 + 3 * 25
    assert sheet["effort"][0]["area"] == "Fundamentos"
    assert sheet["rules"]["grace_days"] == 21

    clock.advance(days=31)  # a sessão de login (14 dias) expira junto: entra de novo
    assert client.get("/api/competencies").status_code == 401
    client.post(
        "/api/auth/login", json={"email": "eu@exemplo.com", "password": PASSWORD}, headers=H
    )
    go = next(c for c in client.get("/api/competencies").json()["competencies"] if c["key"] == "go")
    assert go["status"] == "enferrujando"
    assert go["rust_lost"] > 0


def test_reorder_queue(client: TestClient) -> None:
    register(client)
    add_content(client, "Clean Code")
    second = add_content(client, "Refactoring")
    third = add_content(client, "DDD")
    r = client.put("/api/queue", json={"content_ids": [third["id"]]}, headers=H)
    assert r.status_code == 204
    plan = client.get("/api/plan").json()
    queue = sorted(
        (c for c in plan["contents"] if c["status"] == "LOCKED"), key=lambda c: c["queue_position"]
    )
    assert [c["title"] for c in queue] == ["DDD", "Refactoring"]
    r = client.put("/api/queue", json={"content_ids": [second["id"], second["id"]]}, headers=H)
    assert r.status_code == 422


def test_week_and_preferences(client: TestClient) -> None:
    register(client)
    for title in ("Linux", "Learning Go", "SAST/DAST/SCA", "Docker"):
        add_content(client, title)
    plan = client.get("/api/plan").json()
    assert plan["max_in_progress"] == 3
    assert plan["preferences"] == {"minutes_per_day": 210, "rest_days": []}
    assert sum(c["status"] == "IN_PROGRESS" for c in plan["contents"]) == 3

    r = client.put(
        "/api/plan/preferences", json={"minutes_per_day": 240, "rest_days": [6]}, headers=H
    )
    assert r.status_code == 204
    week = client.get("/api/week").json()
    assert week["minutes_per_day"] == 240
    assert week["pomodoro_minutes"] == 30
    assert len(week["days"]) == 7
    for day in week["days"]:
        assert day["minutes"] == (0 if day["weekday"] == 6 else 240)
        assert day["is_rest"] is (day["weekday"] == 6)

    bad = client.put(
        "/api/plan/preferences", json={"minutes_per_day": 30, "rest_days": []}, headers=H
    )
    assert bad.status_code == 422
    bad = client.put(
        "/api/plan/preferences", json={"minutes_per_day": 200, "rest_days": [9]}, headers=H
    )
    assert bad.status_code == 422
