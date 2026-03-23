"""
SupportPilot AI — Worker process entry point.

Usage (production):
    python -m workers.main

Usage (Docker / Railway):
    CMD ["python", "-m", "workers.main"]

In local dev (USE_KAFKA=false), workers are NOT run separately.
The InMemoryEventBus processes events inline within the FastAPI process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.utils.logging import get_logger
from app.events.topics import Topic
from workers.gmail_poller import gmail_poller
from workers.message_processor import MessageProcessorWorker

logger = get_logger(__name__)


async def main() -> None:
    logger.info(
        "SupportPilot AI Worker starting [USE_KAFKA=%s]", settings.USE_KAFKA
    )

    if not settings.USE_KAFKA:
        logger.warning(
            "USE_KAFKA=false — workers are not needed in local dev mode. "
            "Set USE_KAFKA=true and configure KAFKA_BOOTSTRAP_SERVERS for production."
        )
        return

    # Initialize DB so workers can use it
    from app.core.database import init_db
    await init_db()

    # Instantiate Kafka workers (one per topic)
    kafka_workers = [
        MessageProcessorWorker(),
    ]
    kafka_workers[0].topic = Topic.WEBFORM_INBOUND

    # Kafka consumer tasks
    tasks = [
        asyncio.create_task(w.run_kafka(settings.KAFKA_BOOTSTRAP_SERVERS))
        for w in kafka_workers
    ]

    # Gmail poller (if enabled) — runs independently of Kafka
    if settings.GMAIL_ENABLED:
        await gmail_poller.start()
        logger.info("Gmail poller started")

    logger.info("Started %d Kafka worker(s)", len(tasks))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Worker tasks cancelled — shutting down")
    finally:
        await gmail_poller.stop()
        for task in tasks:
            task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
