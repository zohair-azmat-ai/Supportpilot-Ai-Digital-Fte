"""
SimilarIssueDetector — keyword and metadata based similar issue detection.

Compares the current user message against the user's recent ticket history
to identify previously reported similar issues.  Uses:

  - Normalised keyword overlap (stop-word filtered, min 3-char words)
  - Ticket title + description matching
  - Category match as a secondary signal
  - Ticket resolution status (open / in_progress = unresolved)

Design principles:
  - No embeddings — practical keyword matching covers the common support cases.
  - Fast and cheap — pure Python, no external calls.
  - Safe — any exception degrades to an empty (no-match) result.
  - Excludes tickets belonging to the current conversation (those are the same
    issue, not *similar* issues from a different session).

Similarity threshold:
  KEYWORD_THRESHOLD = 2   — at least 2 shared meaningful keywords
  CATEGORY_BOOST    = 1   — category match reduces keyword requirement by 1
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stop-word set (domain-aware — tuned for support conversations)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    # Pronouns / articles / conjunctions
    "i", "my", "me", "the", "a", "an", "is", "it", "to", "have", "has",
    "am", "are", "was", "be", "of", "in", "for", "and", "or", "but",
    "that", "this", "with", "on", "at", "can", "you", "your", "we",
    "not", "no", "do", "get", "got", "they", "them", "our", "its",
    # Auxiliary / common verbs
    "how", "what", "when", "where", "why", "who", "which",
    "been", "had", "would", "could", "should", "will", "just",
    "also", "need", "want", "trying", "try", "still", "again",
    # Filler / prepositions
    "back", "into", "from", "about", "some", "any", "all", "there",
    "here", "then", "than", "so", "if", "as", "up", "out", "now",
    # Common support filler
    "help", "please", "hi", "hey", "hello", "thanks", "thank",
    "issue", "problem", "issues", "problems",  # too generic for matching
})

# Regex for word extraction: alphabetic only, ≥ 3 characters
_WORD_RE = re.compile(r"\b[a-z]{3,}\b")


def _extract_keywords(text: str) -> frozenset[str]:
    """Extract meaningful, normalised keywords from text."""
    if not text:
        return frozenset()
    words = _WORD_RE.findall(text.lower())
    return frozenset(w for w in words if w not in _STOP_WORDS)


# ---------------------------------------------------------------------------
# SimilarIssueResult
# ---------------------------------------------------------------------------


@dataclass
class SimilarIssueResult:
    """Structured output from SimilarIssueDetector.detect()."""

    similar_issue_found: bool = False
    similar_issue_count: int = 0
    related_ticket_ids: List[str] = field(default_factory=list)
    unresolved_similar_issue_exists: bool = False
    resolved_similar_issue_exists: bool = False
    similar_issue_summary: str = ""   # prompt-ready formatted list


# ---------------------------------------------------------------------------
# SimilarIssueDetector
# ---------------------------------------------------------------------------


class SimilarIssueDetector:
    """Detect similar issues from the user's ticket history.

    Similarity criteria (OR logic):
      1. ≥ KEYWORD_THRESHOLD shared keywords between current message and
         ticket title + description
      2. ≥ (KEYWORD_THRESHOLD - CATEGORY_BOOST) shared keywords AND the
         ticket category matches a category hint derived from message keywords

    Tickets from the current conversation are excluded — those represent the
    same interaction, not a *similar* prior issue.
    """

    KEYWORD_THRESHOLD: int = 2   # shared keywords required for a match
    CATEGORY_BOOST: int = 1      # reduce threshold when category also matches

    # Simple category hints: if message contains any of these words → category
    _CATEGORY_HINTS: dict[str, frozenset[str]] = {
        "account": frozenset({"login", "password", "signin", "access", "locked",
                               "credentials", "username", "authentication"}),
        "billing": frozenset({"payment", "billing", "charge", "refund", "invoice",
                               "subscription", "transaction", "money", "fee", "paid"}),
        "technical": frozenset({"error", "bug", "crash", "broken", "fails",
                                 "working", "loading", "slow", "timeout", "connection"}),
        "complaint": frozenset({"angry", "frustrated", "terrible", "awful",
                                 "disappointed", "unacceptable", "ridiculous"}),
    }

    def detect(
        self,
        user_message: str,
        tickets: List[Any],
        current_conversation_id: Optional[str] = None,
    ) -> SimilarIssueResult:
        """Detect similar issues from the user's ticket history.

        Args:
            user_message:              Raw message text from the customer.
            tickets:                   List of Ticket ORM objects for the user.
            current_conversation_id:   ID of the active conversation (excluded from match).

        Returns:
            SimilarIssueResult — always valid, never raises.
        """
        try:
            return self._detect(user_message, tickets, current_conversation_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SimilarIssueDetector.detect failed (safe fallback): %s", exc)
            return SimilarIssueResult()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _detect(
        self,
        user_message: str,
        tickets: List[Any],
        current_conversation_id: Optional[str],
    ) -> SimilarIssueResult:
        msg_keywords = _extract_keywords(user_message)
        if len(msg_keywords) < 2:
            # Too few meaningful keywords to detect similarity reliably
            return SimilarIssueResult()

        # Derive category hint from message keywords
        msg_category_hint = self._infer_category(msg_keywords)

        similar: list[Any] = []
        unresolved: list[Any] = []
        resolved: list[Any] = []
        summary_lines: list[str] = []

        for ticket in tickets:
            # Skip tickets from the current conversation
            if (
                current_conversation_id
                and getattr(ticket, "conversation_id", None) == current_conversation_id
            ):
                continue

            ticket_text = " ".join(filter(None, [
                getattr(ticket, "title", "") or "",
                getattr(ticket, "description", "") or "",
            ]))
            ticket_keywords = _extract_keywords(ticket_text)

            shared = msg_keywords & ticket_keywords
            shared_count = len(shared)

            # Check category match
            ticket_category = getattr(ticket, "category", "") or ""
            category_matches = (
                msg_category_hint is not None
                and ticket_category == msg_category_hint
            )

            # Determine if this ticket meets the similarity threshold
            effective_threshold = (
                self.KEYWORD_THRESHOLD - self.CATEGORY_BOOST
                if category_matches
                else self.KEYWORD_THRESHOLD
            )
            if shared_count < effective_threshold:
                continue

            similar.append(ticket)
            ticket_status = getattr(ticket, "status", "open") or "open"
            is_unresolved = ticket_status in ("open", "in_progress")

            if is_unresolved:
                unresolved.append(ticket)
            else:
                resolved.append(ticket)

            status_icon = "🔴" if is_unresolved else "✅"
            ticket_id = getattr(ticket, "id", "unknown")
            ticket_title = getattr(ticket, "title", "Untitled") or "Untitled"
            shared_preview = ", ".join(sorted(shared)[:4])
            summary_lines.append(
                f"  {status_icon} [{ticket_id[:8]}] {ticket_title[:60]} "
                f"| status={ticket_status} | category={ticket_category} "
                f"| matched: {shared_preview}"
            )

        if not similar:
            return SimilarIssueResult()

        logger.info(
            "SimilarIssueDetector: found %d similar ticket(s) (%d unresolved)",
            len(similar), len(unresolved),
        )

        return SimilarIssueResult(
            similar_issue_found=True,
            similar_issue_count=len(similar),
            related_ticket_ids=[getattr(t, "id", "") for t in similar],
            unresolved_similar_issue_exists=bool(unresolved),
            resolved_similar_issue_exists=bool(resolved),
            similar_issue_summary="\n".join(summary_lines),
        )

    def _infer_category(self, msg_keywords: frozenset[str]) -> Optional[str]:
        """Infer the likely category from message keywords."""
        for category, hints in self._CATEGORY_HINTS.items():
            if msg_keywords & hints:
                return category
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

similar_issue_detector = SimilarIssueDetector()
