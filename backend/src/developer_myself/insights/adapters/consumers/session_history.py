"""Consumer do histórico: ack manual, prefetch=10, ack só DEPOIS de gravar (ADR-0006)."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from developer_myself.learning.adapters.rabbitmq.topology import SESSION_HISTORY, declare_queue
from developer_myself.shared.correlation import set_correlation_id
from developer_myself.shared.logging import log

Handler = Callable[[dict[str, Any]], Awaitable[bool]]
PREFETCH = 10


async def handle_message(message: AbstractIncomingMessage, handler: Handler) -> None:
    try:
        envelope = json.loads(message.body)
    except json.JSONDecodeError:
        log.error("poison_message", message_id=message.message_id)
        await message.reject(requeue=False)  # vai para a DLQ
        return
    set_correlation_id(envelope.get("correlation_id"))
    try:
        stored = await handler(envelope)
    except Exception:
        log.exception("consumer_error", event_id=envelope.get("event_id"))
        await message.nack(requeue=True)
        return
    await message.ack()
    log.info("event_consumed", event_id=envelope.get("event_id"), duplicate=not stored)


async def consume_session_history(
    connection: AbstractRobustConnection, handler: Handler
) -> aio_pika.abc.AbstractChannel:
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=PREFETCH)
    queue = await declare_queue(channel, SESSION_HISTORY)

    async def on_message(message: AbstractIncomingMessage) -> None:
        await handle_message(message, handler)

    await queue.consume(on_message, no_ack=False)
    return channel
