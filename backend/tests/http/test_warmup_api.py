"""API do aquecimento: GET/POST/DELETE /api/warmup e POST /api/warmup/finish."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.http.test_api import NOTES, H, add_content, register

from developer_myself.composition.container import build_memory_container, create_app
from developer_myself.identity.adapters.memory.repositories import PlainTextHasherForTests
from developer_myself.shared.clock import FakeClock
from developer_myself.shared.settings import Settings


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(clock: FakeClock) -> Iterator[TestClient]:
    settings = Settings(storage="memory", cookie_secure=False, log_json=False, log_level="WARNING")
    container = build_memory_container(settings, clock=clock, hasher=PlainTextHasherForTests())
    with TestClient(create_app(settings, container)) as c:
        yield c


def study_yesterday(client: TestClient, clock: FakeClock, content_id: str, **extra: Any) -> None:
    client.post("/api/sessions", json={"content_id": content_id}, headers=H)
    clock.advance(minutes=25)
    r = client.post("/api/sessions/current/finish", json={**NOTES, **extra}, headers=H)
    assert r.status_code == 200, r.text
    clock.advance(days=1)


def graded(questions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "answers": [
            {"question_id": q["id"], "answer": "lembrei", "grade": "RECALLED"} for q in questions
        ]
    }


def ready(client: TestClient, clock: FakeClock) -> dict[str, Any]:
    register(client)
    content = add_content(client, "Clean Code")
    study_yesterday(client, clock, content["id"])
    return content


def test_full_flow(client: TestClient, clock: FakeClock) -> None:
    content = ready(client, clock)
    status = client.get("/api/warmup").json()
    assert status == {
        "available": True,
        "done_today": False,
        "content": {"id": content["id"], "title": "Clean Code"},
        "active": None,
    }
    started = client.post("/api/warmup", headers=H)
    assert started.status_code == 201, started.text
    questions = started.json()["questions"]
    assert len(questions) == 2
    assert client.get("/api/warmup").json()["active"]["questions"] == questions

    clock.advance(minutes=2)
    done = client.post("/api/warmup/finish", json=graded(questions), headers=H)
    assert done.status_code == 200, done.text
    assert done.json() == {
        "next": {"content_id": content["id"], "title": "Clean Code", "kind": "STUDY"}
    }
    after = client.get("/api/warmup").json()
    assert (after["available"], after["done_today"], after["active"]) == (False, True, None)


def test_start_again_returns_same_questions(client: TestClient, clock: FakeClock) -> None:
    ready(client, clock)
    first = client.post("/api/warmup", headers=H).json()
    clock.advance(minutes=1)
    assert client.post("/api/warmup", headers=H).json() == first


def test_finish_without_answers_is_422(client: TestClient, clock: FakeClock) -> None:
    ready(client, clock)
    client.post("/api/warmup", headers=H)
    r = client.post("/api/warmup/finish", json={"answers": []}, headers=H)
    assert r.status_code == 422
    assert r.json()["code"] == "RecallTestRequiredError"


def test_finish_twice_is_409(client: TestClient, clock: FakeClock) -> None:
    ready(client, clock)
    questions = client.post("/api/warmup", headers=H).json()["questions"]
    assert client.post("/api/warmup/finish", json=graded(questions), headers=H).status_code == 200
    again = client.post("/api/warmup/finish", json=graded(questions), headers=H)
    assert again.status_code == 409
    assert again.json()["code"] == "NoActiveWarmupError"


def test_cancel_then_finish_is_409(client: TestClient, clock: FakeClock) -> None:
    ready(client, clock)
    questions = client.post("/api/warmup", headers=H).json()["questions"]
    assert client.delete("/api/warmup", headers=H).status_code == 204
    r = client.post("/api/warmup/finish", json=graded(questions), headers=H)
    assert r.status_code == 409


def test_nothing_to_warm_up_is_422(client: TestClient) -> None:
    register(client)
    add_content(client, "Clean Code")
    assert client.get("/api/warmup").json()["available"] is False
    r = client.post("/api/warmup", headers=H)
    assert r.status_code == 422
    assert r.json()["code"] == "NothingToWarmUpError"


def test_requires_login(client: TestClient) -> None:
    assert client.get("/api/warmup").status_code == 401
    assert client.post("/api/warmup", headers=H).status_code == 401


def test_future_question_comes_back_with_expected_answer(
    client: TestClient, clock: FakeClock
) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    future = {"text": "O que é CQS?", "answer": "Separar comando de consulta"}
    study_yesterday(client, clock, content["id"], future_question=future)
    first = client.post("/api/warmup", headers=H).json()["questions"][0]
    assert first["text"] == "O que é CQS?"
    assert first["source"] == "LEARNER"
    assert first["expected_answer"] == "Separar comando de consulta"


def test_future_question_is_validated(client: TestClient, clock: FakeClock) -> None:
    register(client)
    content = add_content(client, "Clean Code")
    client.post("/api/sessions", json={"content_id": content["id"]}, headers=H)
    clock.advance(minutes=25)
    long = {**NOTES, "future_question": {"text": "a" * 501}}
    assert client.post("/api/sessions/current/finish", json=long, headers=H).status_code == 422
