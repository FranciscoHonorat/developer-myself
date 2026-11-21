"""Contrato da porta do cadastro: memória e Mongo se comportam igual (ADR-0003)."""

import uuid
from collections.abc import AsyncIterator, Callable

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from tests.integration.conftest import requires_docker

from developer_myself.identity.adapters.memory.repositories import InMemoryRegistrationGate
from developer_myself.identity.adapters.mongo.repositories import MongoRegistrationGate
from developer_myself.identity.application.ports import RegistrationGate
from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client

# Fábrica: cada chamada é uma "instância nova do serviço" sobre o mesmo armazenamento.
GateFactory = Callable[[], RegistrationGate]


@pytest.fixture(
    params=["memory", pytest.param("mongo", marks=[pytest.mark.integration, requires_docker])]
)
async def new_gate(request: pytest.FixtureRequest) -> AsyncIterator[GateFactory]:
    if request.param == "memory":
        shared = InMemoryRegistrationGate()
        yield lambda: shared
        return
    url: str = request.getfixturevalue("mongo_url")
    client = make_client(url)
    name = f"contract_gate_{uuid.uuid4().hex[:12]}"
    db: AsyncDatabase[Doc] = client[name]
    await ensure_schema(db)
    yield lambda: MongoRegistrationGate(db.app_settings)
    await client.drop_database(name)
    await client.close()


async def test_registration_starts_open(new_gate: GateFactory) -> None:
    assert await new_gate().is_open()


async def test_closing_survives_a_restart(new_gate: GateFactory) -> None:
    await new_gate().set_open(False)
    assert not await new_gate().is_open()


async def test_reopening(new_gate: GateFactory) -> None:
    gate = new_gate()
    await gate.set_open(False)
    await gate.set_open(True)
    assert await new_gate().is_open()
