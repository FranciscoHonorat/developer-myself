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


def answer_all(client: TestClient, grade: str = "RECALLED") -> list[dict[str, Any]]:
    """Responde e corrige o teste de memória da sessão ativa."""
    active = client.get("/api/plan").json()["active_session"]
    return [
        {"question_id": q["id"], "answer": "minha resposta", "grade": grade}
        for q in active["questions"]
    ]


def start_review(client: TestClient, clock: FakeClock) -> str:
    register(client)
    content = add_content(client, "Clean Code")
    consolidate(client, clock, content["id"])
    client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    clock.advance(minutes=25)
    return str(content["id"])


def test_review_session_exposes_three_questions(client: TestClient, clock: FakeClock) -> None:
    start_review(client, clock)
    active = client.get("/api/plan").json()["active_session"]
    assert len(active["questions"]) == 3
    assert set(active["questions"][0]) == {"id", "text", "source"}
    assert active["last_to_review"] == NOTES["to_review"]
    assert client.get("/api/plan").json()["contents"][0]["last_to_review"] == NOTES["to_review"]


def test_finish_review_without_answers_is_422(client: TestClient, clock: FakeClock) -> None:
    start_review(client, clock)
    r = client.post("/api/sessions/current/finish", json={**NOTES, "recall_rating": 3}, headers=H)
    assert r.status_code == 422
    assert r.json()["code"] == "RecallTestRequiredError"


def test_finish_review_with_answers_records_the_test(client: TestClient, clock: FakeClock) -> None:
    start_review(client, clock)
    body = {**NOTES, "recall_rating": 2, "answers": answer_all(client, "PARTIAL")}
    r = client.post("/api/sessions/current/finish", json=body, headers=H)
    assert r.status_code == 200
    test = client.get("/api/history").json()["items"][0]["recall_test"]
    assert len(test) == 3
    assert {i["grade"] for i in test} == {"PARTIAL"}
    assert set(test[0]) == {"text", "source", "answer", "grade", "useful"}


def test_invalid_grade_is_422(client: TestClient, clock: FakeClock) -> None:
    start_review(client, clock)
    answers = [{**a, "grade": "TALVEZ"} for a in answer_all(client)]
    body = {**NOTES, "recall_rating": 3, "answers": answers}
    r = client.post("/api/sessions/current/finish", json=body, headers=H)
    assert r.status_code == 422


def test_study_history_has_empty_recall_test(client: TestClient, clock: FakeClock) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    clock.advance(minutes=25)
    client.post("/api/sessions/current/finish", json=NOTES, headers=H)
    assert client.get("/api/history").json()["items"][0]["recall_test"] == []


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

    history = client.get("/api/history").json()["items"]
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

    body = {**NOTES, "recall_rating": 3, "answers": answer_all(client)}
    r = client.post("/api/sessions/current/finish", json=body, headers=H)
    assert r.status_code == 200
    assert r.json()["kind"] == "REVIEW"
    history = client.get("/api/history").json()["items"]
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


# ------------------------------------------------------------------ caderno da matéria
def notebook_url(content_id: str) -> str:
    return f"/api/contents/{content_id}/notebook"


def test_notebook_starts_empty(client: TestClient) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    r = client.get(notebook_url(content["id"]))
    assert r.status_code == 200
    assert r.json() == {
        "content_id": content["id"],
        "text": "",
        "version": 0,
        "updated_at": None,
    }


def test_notebook_save_and_read_back(client: TestClient) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    r = client.put(notebook_url(content["id"]), json={"text": "conceito", "version": 0}, headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 1
    assert r.json()["updated_at"] is not None
    assert client.get(notebook_url(content["id"])).json()["text"] == "conceito"


def test_notebook_stale_version_is_409(client: TestClient) -> None:
    register(client)
    url = notebook_url(add_content(client, "Clean Code")["id"])
    assert client.put(url, json={"text": "aba 1", "version": 0}, headers=H).status_code == 200
    r = client.put(url, json={"text": "aba 2", "version": 0}, headers=H)
    assert r.status_code == 409
    assert r.json()["code"] == "NotebookConflictError"


def test_notebook_of_another_learner_is_404(client: TestClient) -> None:
    register(client, "a@exemplo.com")
    url = notebook_url(add_content(client, "Clean Code")["id"])
    client.put(url, json={"text": "segredo", "version": 0}, headers=H)
    client.post("/api/auth/logout", headers=H)
    register(client, "b@exemplo.com")
    assert client.get(url).status_code == 404
    assert client.put(url, json={"text": "invasão", "version": 1}, headers=H).status_code == 404


def test_notebook_too_long_is_422(client: TestClient) -> None:
    register(client)
    url = notebook_url(add_content(client, "Clean Code")["id"])
    r = client.put(url, json={"text": "a" * 100_001, "version": 0}, headers=H)
    assert r.status_code == 422


def test_notebooks_list_summarizes(client: TestClient) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    client.put(notebook_url(content["id"]), json={"text": "conceito", "version": 0}, headers=H)
    [item] = client.get("/api/notebooks").json()
    assert item["content_id"] == content["id"]
    assert item["chars"] == 8
    assert item["updated_at"] is not None


def test_put_notebook_requires_csrf_header(client: TestClient) -> None:
    register(client)
    url = notebook_url(add_content(client, "Clean Code")["id"])
    assert client.put(url, json={"text": "x", "version": 0}).status_code == 403


def test_export_includes_notebooks_and_delete_account_erases_them(client: TestClient) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    client.put(notebook_url(content["id"]), json={"text": "conceito", "version": 0}, headers=H)
    exported = client.get("/api/export").json()
    assert exported["notebooks"] == [
        {
            "content_id": content["id"],
            "text": "conceito",
            "updated_at": exported["notebooks"][0]["updated_at"],
        }
    ]
    learner_id = client.get("/api/auth/me").json()["id"]
    container = client.app.state.container  # type: ignore[attr-defined]
    client.post("/api/auth/delete-account", json={"password": PASSWORD}, headers=H)
    assert client.portal.call(container.learning.notebooks.list, uuid.UUID(learner_id)) == []  # type: ignore[union-attr]


def test_history_is_paginated_by_cursor(client: TestClient, clock: FakeClock) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    for _ in range(3):
        client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
        clock.advance(minutes=25)
        client.post("/api/sessions/current/finish", json=NOTES, headers=H)

    first = client.get("/api/history", params={"limit": 2}).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"]
    second = client.get("/api/history", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None
    seen = [s["event_id"] for s in first["items"] + second["items"]]
    assert len(set(seen)) == 3


@pytest.mark.parametrize("cursor", ["lixo", "e30", "eyJ0IjoiMjAyNiJ9"])
def test_history_rejects_a_tampered_cursor(client: TestClient, cursor: str) -> None:
    register(client)
    r = client.get("/api/history", params={"cursor": cursor})
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_CURSOR"


def test_history_page_size_is_bounded(client: TestClient) -> None:
    register(client)
    assert client.get("/api/history", params={"limit": 101}).status_code == 422
