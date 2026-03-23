"""Abstract base class for all SupportPilot workers."""

from __future__ import annotations

import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Abstract base for all background workers.

    Workers run as standalone processes and consume events from the event bus
    (Kafka in production, in-memory in dev).

    Subclasses implement:
    - topic: str — the Kafka topic to consume from
    - process(event: dict) — handle one event
    """

    topic: str = ""
    worker_name: str = "base_worker"

    def __init__(self) -> None:
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    @abstractmethod
    async def process(self, event: dict[str, Any]) -> None:
        """Process a single event payload."""
        ...

    async def on_start(self) -> None:
        """Called once before the consume loop. Override for setup."""
        pass

    async def on_stop(self) -> None:
        """Called once after the consume loop. Override for cleanup."""
        pass

    async def run_kafka(self, bootstrap_servers: str) -> None:
        """Consume from Kafka topic and process events."""
        from aiokafka import AIOKafkaConsumer  # type: ignore

        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=bootstrap_servers,
            group_id=f"supportpilot_{self.worker_name}",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

        await self.on_start()
        await consumer.start()
        self._running = True
        logger.info(
            "%s started consuming from topic: %s", self.worker_name, self.topic
        )

        def _handle_signal(sig: int, frame: Any) -> None:
            logger.info(
                "%s received signal %s — shutting down", self.worker_name, sig
            )
            self._running = False

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    import json

                    event = json.loads(msg.value.decode("utf-8"))
                    await self.process(event)
                    self._processed_count += 1
                    logger.debug(
                        "%s processed event from %s",
                        self.worker_name,
                        self.topic,
                    )
                except Exception as exc:
                    self._error_count += 1
                    logger.error(
                        "%s failed to process event: %s",
                        self.worker_name,
                        exc,
                        exc_info=True,
                    )
        finally:
            await consumer.stop()
            await self.on_stop()
            logger.info(
                "%s stopped. processed=%d errors=%d",
                self.worker_name,
                self._processed_count,
                self._error_count,
            )

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "worker": self.worker_name,
            "topic": self.topic,
            "running": self._running,
            "processed": self._processed_count,
            "errors": self._error_count,
        }
