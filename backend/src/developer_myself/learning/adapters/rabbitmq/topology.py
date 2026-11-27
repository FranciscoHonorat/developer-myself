"""Topologia RabbitMQ 4.x (ADR-0006).

exchange learning.events (topic, durable)
  ├─ learning.study_session_{finished,abandoned}.v1 ─▶ insights.session-history (quorum)
  └─ learning.warmup_finished.v1                   ─▶ insights.session-history
DLX learning.dlx (direct) ─▶ <fila>.dlq
"""

from dataclasses import dataclass

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

EVENTS_EXCHANGE = "learning.events"
DLX = "learning.dlx"
DELIVERY_LIMIT = 5


@dataclass(frozen=True, slots=True)
class QueueSpec:
    name: str
    bindings: tuple[str, ...]


SESSION_HISTORY = QueueSpec(
    name="insights.session-history",
    bindings=(
        "learning.study_session_finished.v1",
        "learning.study_session_abandoned.v1",
        "learning.warmup_finished.v1",
    ),
)


async def declare_exchange(channel: AbstractChannel) -> AbstractExchange:
    return await channel.declare_exchange(
        EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
    )


async def declare_queue(channel: AbstractChannel, spec: QueueSpec) -> AbstractQueue:
    exchange = await declare_exchange(channel)
    dlx = await channel.declare_exchange(DLX, aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await channel.declare_queue(
        f"{spec.name}.dlq", durable=True, arguments={"x-queue-type": "quorum"}
    )
    await dlq.bind(dlx, routing_key=spec.name)
    queue = await channel.declare_queue(
        spec.name,
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-delivery-limit": DELIVERY_LIMIT,
            "x-dead-letter-exchange": DLX,
            "x-dead-letter-routing-key": spec.name,
        },
    )
    for key in spec.bindings:
        await queue.bind(exchange, routing_key=key)
    return queue
