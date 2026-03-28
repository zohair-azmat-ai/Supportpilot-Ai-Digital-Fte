"""
MemoryService — lightweight conversation and user memory layer.

Two distinct memory scopes:
  - Conversation memory  (short-term, within a single session)
  - User memory          (cross-session, user's support history)

Both are read-only wrappers around existing DB repositories and the
ConversationContextBuilder.  No new tables are needed.

Rules enforced by design:
  - No escalation leakage across sessions on first contact.
  - No false repeated-issue detection from cross-session history.
  - First-contact messages always return clean, empty issue signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Memory result types
# ---------------------------------------------------------------------------


@dataclass
class ConversationMemory:
    """Short-term memory scoped to the current conversation session.

    Attributes:
        conversation_id: ID of the active conversation.
        turn_count:       Number of completed user turns.
        is_first_contact: True when this is the user's first message.
        recent_messages:  Last N messages [{sender_type, content}].
        last_ai_reply:    Most recent AI response text (empty string if none).
        user_frustrated:  True if frustration keywords detected in session.
        failed_attempts:  Count of failed-attempt signals in session.
        repeated_issue:   True if topic overlap across turns detected.
    """

    conversation_id: str
    turn_count: int = 0
    is_first_contact: bool = True
    recent_messages: List[dict] = field(default_factory=list)
    last_ai_reply: str = ""
    user_frustrated: bool = False
    failed_attempts: int = 0
    repeated_issue: bool = False


@dataclass
class UserMemory:
    """Cross-session memory for a specific user.

    Contains the user's support history without implying ongoing issues
    for new (first-contact) messages.

    Attributes:
        user_id:                  The user's ID.
        has_prior_history:        True if any tickets or conversations exist.
        open_ticket_count:        Number of currently open/in-progress tickets.
        prior_escalation_history: True if any past conversation was escalated.
        recent_ticket_summaries:  Brief summaries of the last 5 tickets.
        recent_channel_history:   Channels the user has previously used.
    """

    user_id: str
    has_prior_history: bool = False
    open_ticket_count: int = 0
    prior_escalation_history: bool = False
    recent_ticket_summaries: List[str] = field(default_factory=list)
    recent_channel_history: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MemoryService
# ---------------------------------------------------------------------------


class MemoryService:
    """Reads conversation and user memory from the DB.

    Uses existing repositories — no extra tables required.
    """

    async def get_conversation_memory(
        self,
        db: Any,
        conversation_id: str,
        limit: int = 10,
    ) -> ConversationMemory:
        """Return short-term memory for the active conversation.

        Args:
            db:              AsyncSession.
            conversation_id: ID of the conversation to read.
            limit:           Max number of recent messages to include.

        Returns:
            ConversationMemory — always valid, never raises.
        """
        try:
            from app.repositories.conversation import ConversationRepository

            conv_repo = ConversationRepository(db)
            conv = await conv_repo.get_with_messages(conversation_id)

            if conv is None:
                logger.warning("MemoryService: conversation %s not found", conversation_id)
                return ConversationMemory(conversation_id=conversation_id)

            messages = conv.messages or []
            recent = [
                {"sender_type": m.sender_type, "content": m.content}
                for m in messages[-limit:]
                if m.content
            ]

            user_turns = [m for m in messages if m.sender_type == "user"]
            turn_count = len(user_turns)
            is_first_contact = turn_count == 0

            last_ai_reply = ""
            for m in reversed(messages):
                if m.sender_type in ("ai", "agent") and m.content:
                    last_ai_reply = m.content.strip()
                    break

            return ConversationMemory(
                conversation_id=conversation_id,
                turn_count=turn_count,
                is_first_contact=is_first_contact,
                recent_messages=recent,
                last_ai_reply=last_ai_reply,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MemoryService.get_conversation_memory failed for conv=%s: %s",
                conversation_id, exc,
            )
            return ConversationMemory(conversation_id=conversation_id)

    async def get_user_memory(
        self,
        db: Any,
        user_id: str,
    ) -> UserMemory:
        """Return cross-session memory for a user.

        Never implies 'ongoing issue' — callers should use this only to
        provide neutral history context, not to signal repeated problems.

        Args:
            db:      AsyncSession.
            user_id: The user's ID.

        Returns:
            UserMemory — always valid, never raises.
        """
        try:
            from app.repositories.ticket import TicketRepository
            from app.repositories.conversation import ConversationRepository

            ticket_repo = TicketRepository(db)
            conv_repo = ConversationRepository(db)

            tickets = await ticket_repo.get_by_user(user_id, skip=0, limit=10)
            conversations = await conv_repo.get_by_user(user_id, skip=0, limit=4)

            has_prior_history = bool(tickets or conversations)
            open_ticket_count = sum(
                1 for t in tickets if getattr(t, "status", "") in ("open", "in_progress")
            )
            prior_escalation = any(
                getattr(c, "status", "") == "escalated" for c in (conversations or [])
            )

            ticket_summaries = [
                f"{t.title} [{t.status}]"
                for t in (tickets or [])[:5]
                if t.title
            ]

            channels = list({
                getattr(c, "channel", None)
                for c in (conversations or [])
                if getattr(c, "channel", None)
            })

            return UserMemory(
                user_id=user_id,
                has_prior_history=has_prior_history,
                open_ticket_count=open_ticket_count,
                prior_escalation_history=prior_escalation,
                recent_ticket_summaries=ticket_summaries,
                recent_channel_history=sorted(channels),
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MemoryService.get_user_memory failed for user=%s: %s",
                user_id, exc,
            )
            return UserMemory(user_id=user_id)

    async def write_conversation_note(
        self,
        db: Any,
        conversation_id: str,
        note: str,
    ) -> bool:
        """Append a note to a conversation's metadata (best-effort).

        Args:
            db:              AsyncSession.
            conversation_id: Target conversation.
            note:            Free-text note to store.

        Returns:
            True on success, False on failure.
        """
        try:
            from app.repositories.conversation import ConversationRepository

            conv_repo = ConversationRepository(db)
            conv = await conv_repo.get(conversation_id)
            if conv is None:
                return False

            existing = dict(getattr(conv, "metadata_", None) or {})
            notes: list = existing.get("notes", [])
            notes.append(note)
            await conv_repo.update(conversation_id, {"metadata_": {**existing, "notes": notes}})
            return True

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "MemoryService.write_conversation_note failed: %s", exc
            )
            return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

memory_service = MemoryService()
