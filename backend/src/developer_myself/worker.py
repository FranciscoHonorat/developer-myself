"""Processo `worker`: relay do outbox + consumers (ADR-0006, ADR-0010).

Mesma imagem da API, outro comando: `python -m developer_myself.worker`.
"""

import asyncio
import contextlib
import signal

import aio_pika

from developer_myself.insights.adapters.consumers.session_history import consume_session_history
from developer_myself.learning.adapters.mongo.outbox_relay import OutboxRelay
from developer_myself.learning.adapters.rabbitmq.publisher import RabbitPublisher
from developer_myself.mongo_bootstrap import build_mongo_container
from developer_myself.shared.adapters.mongo_setup import make_client
from developer_myself.shared.logging import configure_logging, log
from developer_myself.shared.settings import Settings


async def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level, json=settings.log_json)
    if settings.rabbit_url is None:
        raise SystemExit("DM_RABBIT_URL é obrigatório para o worker.")

    container = await build_mongo_container(settings)
    client = make_client(settings.mongo_url.get_secret_value())
    connection = await aio_pika.connect_robust(settings.rabbit_url.get_secret_value())

    publisher = await RabbitPublisher.create(connection)
    relay = OutboxRelay(client[settings.mongo_db].study_plans, publisher.publish)
    await consume_session_history(connection, container.record_history)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    log.info("worker_started")
    try:
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(relay.run_forever(settings.relay_interval_seconds, stop))
            tasks.create_task(
                container.retrain_job.run_forever(settings.retrain_interval_seconds, stop)
            )
    finally:
        await connection.close()
        await client.close()
        await container.close()
        log.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
