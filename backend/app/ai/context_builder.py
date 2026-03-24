"""
ConversationContextBuilder — Step 2 of the Level 4 AI upgrade.

Builds a structured ConversationContext for every incoming message by:

  1. Analysing the current conversation history to derive repeat/frustration signals.
  2. Fetching the user's recent tickets and conversations from the DB to detect
     cross-session patterns (open tickets, prior escalations).
  3. Packaging everything into a prompt-ready block injected into the LLM call.

All DB lookups are wrapped in try/except — a failed lookup degrades gracefully to
signals derived from conversation history only.  The request never crashes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal keyword sets
# ---------------------------------------------------------------------------

_FRUSTRATION_KEYWORDS = frozenset({
    "frustrated", "annoyed", "angry", "furious", "ridiculous",
    "useless", "terrible", "awful", "unacceptable", "waste of time",
    "this is not helping", "not good enough", "sick of this",
    "how many times", "still not working", "nothing works",
    "same problem", "same issue", "keeps happening", "still broken",
    "still failing", "still can't", "still cannot", "still not",
    "not resolved", "unresolved", "not fixed",
})

_FAILED_ATTEMPT_KEYWORDS = frozenset({
    "tried", "already tried", "already did", "i did that",
    "not working", "didn't work", "doesn't work",
    "same issue", "same problem", "still not", "still can't",
    "tried again", "tried multiple", "tried everything",
    "nothing works", "no luck", "keeps happening",
})

_REPEATED_ISSUE_KEYWORDS = frozenset({
    "again", "still", "same", "back again", "still not", "still can't",
    "not working", "not fixed", "unresolved", "same problem",
    "same issue", "happening again", "keeps happening", "tried already",
})

_ESCALATION_PHRASES = frozenset({
    "escalat", "human agent", "human support", "speak to someone",
    "talk to a person", "connect me to", "real person",
})

_STOP_WORDS = frozenset({
    "i", "my", "me", "the", "a", "an", "is", "it", "to", "have", "has",
    "am", "are", "was", "be", "of", "in", "for", "and", "or", "but",
    "that", "this", "with", "on", "at", "can", "you", "your", "we",
    "not", "no", "do", "get", "got", "help", "please", "hi", "hey",
})


# ---------------------------------------------------------------------------
# ConversationContext dataclass
# ---------------------------------------------------------------------------


@dataclass
class ConversationContext:
    """All context signals available before the LLM call.

    Derived from two sources:
      - Conversation history (same session, in-memory)
      - User's recent tickets / conversations (cross-session, from DB)
    """

    # --- Repeat / frustration signals ---
    repeated_issue: bool = False
    user_frustrated: bool = False
    previous_failed_attempts: int = 0
    related_open_ticket_exists: bool = False
    prior_escalation_in_session: bool = False
    prior_escalation_in_history: bool = False

    # --- Session metadata ---
    message_count_in_session: int = 0   # number of prior user turns
    is_first_contact: bool = True

    # --- Similar issue signals (cross-session ticket comparison) ---
    similar_issue_found: bool = False
    similar_issue_count: int = 0
    related_ticket_ids: list = field(default_factory=list)
    unresolved_similar_issue_exists: bool = False
    similar_issue_summary: str = ""     # formatted for prompt injection

    # --- Content for prompt injection ---
    last_ai_reply: str = ""             # used to prevent verbatim repetition
    user_history_summary: str = ""      # formatted recent ticket/conv summary

    def to_prompt_block(self) -> str:
        """Format as a concise context block for the LLM system message.

        Keeps the block short (< 400 chars) so it doesn't dominate the
        context window.  Only adds lines for signals that are active.
        """
        lines: list[str] = ["[CONVERSATION CONTEXT]"]

        if self.is_first_contact:
            lines.append("Turn: 1 (first message in this session — do NOT escalate unless critical)")
        else:
            lines.append(f"Turn: {self.message_count_in_session + 1}")

        if self.repeated_issue:
            attempts = self.previous_failed_attempts
            label = f"{attempts} prior failed attempt(s)" if attempts else "similar topic raised before"
            lines.append(f"⚠ Repeated issue — {label}. Vary your approach; do not repeat the same steps.")

        if self.user_frustrated:
            lines.append("⚠ User appears frustrated. Lead with empathy. Be brief. Do not list steps they already tried.")

        if self.previous_failed_attempts >= 2 and not self.user_frustrated:
            lines.append(f"⚠ {self.previous_failed_attempts} failed attempts detected. Consider escalation if issue persists.")

        if self.related_open_ticket_exists:
            lines.append("⚠ An open ticket already exists for this user. This may be an ongoing unresolved issue.")

        if self.similar_issue_found:
            status_label = (
                "UNRESOLVED — do NOT repeat previous troubleshooting steps"
                if self.unresolved_similar_issue_exists
                else "previously resolved"
            )
            lines.append(
                f"⚠ Similar issue history: {self.similar_issue_count} related "
                f"ticket(s) found ({status_label})."
            )
            if self.unresolved_similar_issue_exists:
                lines.append(
                    "  Acknowledge the existing issue. Avoid generic troubleshooting. "
                    "Consider escalation or referencing the open ticket."
                )

        if self.prior_escalation_in_session:
            lines.append("⚠ A prior escalation occurred in this session. Treat with high priority.")

        if self.prior_escalation_in_history:
            lines.append("⚠ User has been escalated in a previous session. Handle carefully.")

        if self.similar_issue_summary:
            lines.append(f"\nSimilar past issues:\n{self.similar_issue_summary}")

        if self.user_history_summary:
            lines.append(f"\nRecent support history:\n{self.user_history_summary}")

        if self.last_ai_reply:
            # Truncate to keep prompt tight
            preview = self.last_ai_reply[:180]
            if len(self.last_ai_reply) > 180:
                preview += "…"
            lines.append(f'\nDo NOT repeat this previous reply verbatim:\n"{preview}"')

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ConversationContextBuilder
# ---------------------------------------------------------------------------


class ConversationContextBuilder:
    """Builds a ConversationContext from message history + optional DB lookup."""

    async def build(
        self,
        db: Any,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
    ) -> ConversationContext:
        """Build a ConversationContext for the current message.

        Args:
            db: AsyncSession — may be None in tests; DB lookups are skipped if so.
            user_id: The customer's user ID.
            user_message: The latest message text from the customer.
            conversation_history: Prior messages [{sender_type, content}, ...].

        Returns:
            ConversationContext — always valid, never raises.
        """
        ctx = ConversationContext()

        # --- Signals from in-session history ---
        self._derive_in_session_signals(ctx, user_message, conversation_history)

        # --- Cross-session signals from DB (safe fallback) ---
        if db is not None:
            await self._fetch_user_history(ctx, db, user_id, user_message)

        return ctx

    # ------------------------------------------------------------------
    # In-session signal derivation
    # ------------------------------------------------------------------

    def _derive_in_session_signals(
        self,
        ctx: ConversationContext,
        user_message: str,
        conversation_history: list[dict],
    ) -> None:
        """Derive all signals that can be computed from conversation history alone."""
        msg = user_message.lower().strip()

        prior_user_msgs: list[str] = [
            m.get("content", "").lower()
            for m in conversation_history
            if m.get("sender_type") == "user" and m.get("content")
        ]

        ctx.message_count_in_session = len(prior_user_msgs)
        ctx.is_first_contact = ctx.message_count_in_session == 0

        # --- Frustration ---
        ctx.user_frustrated = any(kw in msg for kw in _FRUSTRATION_KEYWORDS)
        if not ctx.user_frustrated and prior_user_msgs:
            # Also check the most recent prior message for frustration build-up
            ctx.user_frustrated = any(
                kw in prior_user_msgs[-1] for kw in _FRUSTRATION_KEYWORDS
            )

        # --- Failed attempts (count prior user turns with failure keywords) ---
        ctx.previous_failed_attempts = sum(
            1 for m in prior_user_msgs
            if any(kw in m for kw in _FAILED_ATTEMPT_KEYWORDS)
        )
        # Also count the current message
        if any(kw in msg for kw in _FAILED_ATTEMPT_KEYWORDS):
            ctx.previous_failed_attempts += 1

        # --- Repeated issue (topic overlap across recent turns) ---
        current_words = set(msg.split()) - _STOP_WORDS
        if len(prior_user_msgs) >= 1 and len(current_words) >= 2:
            overlap_count = sum(
                1
                for prev in prior_user_msgs[-8:]
                if len((set(prev.split()) - _STOP_WORDS) & current_words) >= 2
            )
            if overlap_count >= 2:
                ctx.repeated_issue = True

        # Also flag via explicit repeated-issue keywords in current message
        if any(kw in msg for kw in _REPEATED_ISSUE_KEYWORDS):
            ctx.repeated_issue = True
            ctx.previous_failed_attempts = max(ctx.previous_failed_attempts, 1)

        # --- Prior escalation in this session (check AI messages) ---
        for m in conversation_history:
            if m.get("sender_type") in ("ai", "agent"):
                content = m.get("content", "").lower()
                if any(phrase in content for phrase in _ESCALATION_PHRASES):
                    ctx.prior_escalation_in_session = True
                    break

        # --- Last AI reply (for response variation) ---
        for m in reversed(conversation_history):
            if m.get("sender_type") in ("ai", "agent") and m.get("content"):
                ctx.last_ai_reply = m["content"].strip()
                break

    # ------------------------------------------------------------------
    # Cross-session DB lookup
    # ------------------------------------------------------------------

    async def _fetch_user_history(
        self,
        ctx: ConversationContext,
        db: Any,
        user_id: str,
        user_message: str = "",
    ) -> None:
        """Fetch and summarise the user's recent tickets and conversations.

        Populates:
          - ctx.related_open_ticket_exists
          - ctx.prior_escalation_in_history
          - ctx.user_history_summary
          - ctx.similar_issue_found / similar_issue_count / related_ticket_ids
          - ctx.unresolved_similar_issue_exists / similar_issue_summary

        All exceptions are caught — failure here never crashes the request.
        """
        try:
            from app.repositories.ticket import TicketRepository
            from app.repositories.conversation import ConversationRepository
            from app.ai.similar_issue_detector import similar_issue_detector

            ticket_repo = TicketRepository(db)
            conv_repo = ConversationRepository(db)

            tickets = await ticket_repo.get_by_user(user_id, skip=0, limit=10)
            conversations = await conv_repo.get_by_user(user_id, skip=0, limit=4)

            lines: list[str] = []

            if tickets:
                for t in tickets[:5]:
                    status_icon = "🔴" if t.status in ("open", "in_progress") else "✅"
                    lines.append(
                        f"  {status_icon} Ticket: \"{t.title}\" | "
                        f"status={t.status} priority={t.priority} category={t.category}"
                    )
                    if t.status in ("open", "in_progress"):
                        ctx.related_open_ticket_exists = True

            if conversations:
                for c in conversations[:3]:
                    if getattr(c, "status", "") == "escalated":
                        ctx.prior_escalation_in_history = True
                    status_icon = "⚠" if getattr(c, "status", "") == "escalated" else "•"
                    subject = f" | subject={c.subject}" if getattr(c, "subject", None) else ""
                    lines.append(
                        f"  {status_icon} Conversation: channel={c.channel} "
                        f"status={c.status}{subject}"
                    )

            if lines:
                ctx.user_history_summary = "\n".join(lines)

            # --- Similar issue detection ---
            if tickets and user_message:
                sim = similar_issue_detector.detect(
                    user_message=user_message,
                    tickets=tickets,
                    current_conversation_id=None,  # no conversation yet at this stage
                )
                if sim.similar_issue_found:
                    ctx.similar_issue_found = True
                    ctx.similar_issue_count = sim.similar_issue_count
                    ctx.related_ticket_ids = sim.related_ticket_ids
                    ctx.unresolved_similar_issue_exists = sim.unresolved_similar_issue_exists
                    ctx.similar_issue_summary = sim.similar_issue_summary
                    logger.info(
                        "Context: %d similar ticket(s) found (%s)",
                        sim.similar_issue_count,
                        "unresolved" if sim.unresolved_similar_issue_exists else "resolved",
                    )

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ConversationContextBuilder: DB lookup failed for user=%s: %s",
                user_id, exc,
            )
            # Signals already derived from in-session history; continue safely.


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

context_builder = ConversationContextBuilder()
