"""
Kafka event bus — production mode.

STATUS: Requires KAFKA_BOOTSTRAP_SERVERS env var and a running Kafka cluster.
For local development, set USE_KAFKA=false (default) to use InMemoryEventBus.

Uses aiokafka for async producer/consumer.
Topics must be pre-created or auto-created (auto.create.topics.enable=true).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)


class KafkaEventBus:
    """
    Async Kafka event bus for production deployments.

    publish() sends a JSON-serialised event to the given topic.
    Workers (backend/workers/) run as separate processes consuming from topics.

    Requires: pip install aiokafka
    """

    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer = None
        self._handlers: Dict[str, List[Callable]] = {}

    async def start(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer  # type: ignore

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            logger.info(
                "KafkaEventBus connected to %s", self._bootstrap_servers
            )
        except ImportError:
            logger.error(
                "aiokafka is not installed. Run: pip install aiokafka>=0.10.0"
            )
            raise
        except Exception as exc:
            logger.error("Failed to connect to Kafka: %s", exc)
            raise

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("KafkaEventBus producer stopped")

    async def publish(self, topic: str, event: Any) -> None:
        """Publish event to Kafka topic. Fire-and-forget."""
        if self._producer is None:
            raise RuntimeError(
                "KafkaEventBus not started. Call start() first."
            )

        payload = event.model_dump() if hasattr(event, "model_dump") else event
        # Serialise datetime fields
        if isinstance(payload, dict):
            payload = {
                k: v.isoformat() if hasattr(v, "isoformat") else v
                for k, v in payload.items()
            }

        await self._producer.send_and_wait(
            topic,
            value=payload,
            key=getattr(event, "event_id", None),
        )
        logger.debug(
            "Published event %s to topic %s",
            getattr(event, "event_id", "?"),
            topic,
        )

    async def subscribe(self, topic: str, handler: Callable[..., Awaitable[Any]]) -> None:
        """Register a handler (used by workers, not the API process)."""
        self._handlers.setdefault(topic, []).append(handler)
