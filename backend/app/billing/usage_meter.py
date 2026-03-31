"""
UsageMeter — tracks per-user message and ticket consumption.

Phase 6 implementation uses an in-memory store for now.
A DB-backed implementation (metering table + monthly reset job) will
replace this when the full billing pipeline is activated.

Usage:
    from app.billing.usage_meter import usage_meter

    await usage_meter.record_message(user_id="u123")
    count = await usage_meter.get_message_count(user_id="u123")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class UserUsage:
    """Current-period usage counters for one user."""
    user_id: str
    message_count: int = 0
    ticket_count: int = 0
    period_start: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity: Optional[datetime] = None


class UsageMeter:
    """In-memory usage tracker (Phase 6 stub).

    Thread-safety note: asyncio single-threaded — no lock needed for
    the current in-process implementation.
    """

    def __init__(self) -> None:
        # user_id → UserUsage
        self._usage: dict[str, UserUsage] = defaultdict(
            lambda: UserUsage(user_id="")
        )

    async def record_message(self, user_id: str, db: Any = None) -> int:
        """Increment the message counter for a user.

        Args:
            user_id: The user whose counter to increment.
            db:      Reserved for future DB-backed implementation.

        Returns:
            New message count for the current period.
        """
        entry = self._get_or_create(user_id)
        entry.message_count += 1
        entry.last_activity = datetime.now(timezone.utc)
        logger.debug("UsageMeter: user=%s messages=%d", user_id, entry.message_count)
        return entry.message_count

    async def record_ticket(self, user_id: str, db: Any = None) -> int:
        """Increment the ticket counter for a user."""
        entry = self._get_or_create(user_id)
        entry.ticket_count += 1
        entry.last_activity = datetime.now(timezone.utc)
        return entry.ticket_count

    async def get_message_count(self, user_id: str) -> int:
        """Return current-period message count for a user."""
        return self._usage.get(user_id, UserUsage(user_id=user_id)).message_count

    async def get_ticket_count(self, user_id: str) -> int:
        """Return current-period ticket count for a user."""
        return self._usage.get(user_id, UserUsage(user_id=user_id)).ticket_count

    async def get_usage(self, user_id: str) -> UserUsage:
        """Return the full usage record for a user."""
        return self._get_or_create(user_id)

    async def reset_user(self, user_id: str) -> None:
        """Reset counters for a user (e.g. on billing period rollover)."""
        if user_id in self._usage:
            del self._usage[user_id]
            logger.info("UsageMeter: reset counters for user=%s", user_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_create(self, user_id: str) -> UserUsage:
        if user_id not in self._usage:
            self._usage[user_id] = UserUsage(user_id=user_id)
        return self._usage[user_id]


# Module-level singleton
usage_meter = UsageMeter()
