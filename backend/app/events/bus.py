"""Abstract event bus interface and in-memory implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
HandlerFn = Callable[[Any], Awaitable[Any]]


class EventBus(ABC):
    """Abstract event bus interface."""

    @abstractmethod
    async def publish(self, topic: str, event: Any) -> Any:
        """Publish an event to a topic. Returns result for in-memory bus, None for Kafka."""
        ...

    @abstractmethod
    async def subscribe(self, topic: str, handler: HandlerFn) -> None:
        """Register a handler for a topic."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the bus (connect to Kafka, etc.)."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the bus."""
        ...


class InMemoryEventBus(EventBus):
    """
    Synchronous in-memory event bus for local development.

    publish() immediately invokes the registered handler and returns its result.
    No Kafka required. API responses are still synchronous — behavior is identical
    to direct service calls.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[HandlerFn]] = {}
        self._published: List[tuple[str, Any]] = []  # audit log

    async def subscribe(self, topic: str, handler: HandlerFn) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, event: Any) -> Any:
        self._published.append((topic, event))
        handlers = self._handlers.get(topic, [])
        result = None
        for handler in handlers:
            result = await handler(event)
        return result

    async def start(self) -> None:
        logger.info("InMemoryEventBus started (no Kafka)")

    async def stop(self) -> None:
        logger.info("InMemoryEventBus stopped")

    @property
    def published_count(self) -> int:
        return len(self._published)


# Module-level singleton — replaced by get_event_bus()
_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return the configured event bus singleton."""
    global _bus_instance
    if _bus_instance is None:
        from app.core.config import settings

        if settings.USE_KAFKA:
            from app.events.kafka_bus import KafkaEventBus

            _bus_instance = KafkaEventBus(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
            )
        else:
            _bus_instance = InMemoryEventBus()
    return _bus_instance


def reset_event_bus() -> None:
    """Reset singleton (useful for testing)."""
    global _bus_instance
    _bus_instance = None
