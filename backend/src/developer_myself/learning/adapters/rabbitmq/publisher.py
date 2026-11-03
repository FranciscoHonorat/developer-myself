"""Publica envelopes com publisher confirms (ADR-0006)."""

import json
from typing import Any

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange

from developer_myself.learning.adapters.rabbitmq.topology import declare_exchange
from developer_myself.shared.events import routing_key


class RabbitPublisher:
    def __init__(self, channel: AbstractChannel, exchange: AbstractExchange) -> None:
        self._channel = channel
        self._exchange = exchange

    @classmethod
    async def create(cls, connection: aio_pika.abc.AbstractRobustConnection) -> RabbitPublisher:
        channel = await connection.channel(publisher_confirms=True)
        return cls(channel, await declare_exchange(channel))

    async def publish(self, envelope: dict[str, Any]) -> None:
        """Retorna só depois do confirm do broker (levanta se ele recusar)."""
        message = aio_pika.Message(
            body=json.dumps(envelope).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=envelope["event_id"],
            correlation_id=envelope.get("correlation_id"),
            type=envelope["type"],
        )
        await self._exchange.publish(
            message, routing_key=routing_key(envelope["type"], envelope["version"]), mandatory=False
        )
