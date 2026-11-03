"""Infra real via Testcontainers (ADR-0008). Pulados automaticamente sem Docker."""

import shutil
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from developer_myself.shared.adapters.mongo_setup import Doc, ensure_schema, make_client


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        import docker  # noqa: PLC0415

        docker.from_env().ping()
    except Exception:
        return False
    return True


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker indisponível")


@pytest.fixture(scope="session")
def mongo_url() -> Iterator[str]:
    from testcontainers.core.container import DockerContainer  # noqa: PLC0415
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy  # noqa: PLC0415

    container = (
        DockerContainer("mongo:8.2")
        .with_command("--replSet rs0 --bind_ip_all")
        .with_exposed_ports(27017)
        .waiting_for(LogMessageWaitStrategy("Waiting for connections"))
    )
    with container:
        container.exec(
            [
                "mongosh",
                "--quiet",
                "--eval",
                "rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]})",
            ]
        )
        host = container.get_container_host_ip()
        port = container.get_exposed_port(27017)
        yield f"mongodb://{host}:{port}/?directConnection=true"


@pytest.fixture
async def mongo_db(mongo_url: str) -> AsyncIterator[AsyncDatabase[Doc]]:
    client: AsyncMongoClient[Doc] = make_client(mongo_url)
    name = f"test_{uuid.uuid4().hex[:12]}"
    db = client[name]
    await ensure_schema(db)
    yield db
    await client.drop_database(name)
    await client.close()


@pytest.fixture(scope="session")
def rabbit_url() -> Iterator[str]:
    from testcontainers.rabbitmq import RabbitMqContainer  # noqa: PLC0415

    with RabbitMqContainer("rabbitmq:4-management") as rabbit:
        host = rabbit.get_container_host_ip()
        port = rabbit.get_exposed_port(5672)
        yield f"amqp://guest:guest@{host}:{port}/"
