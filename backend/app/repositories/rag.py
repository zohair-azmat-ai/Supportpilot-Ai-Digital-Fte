"""
RAGRepository — message-content based similar issue retrieval.

Searches the messages table for past user messages whose content overlaps
with the current query, then fetches the assistant response that followed
each match.  Returns (user issue, solution) pairs for injection into the
LLM system message.

How it differs from SimilarIssueDetector:
  - SimilarIssueDetector compares ticket TITLES/DESCRIPTIONS (structured data)
  - RAGRepository compares raw MESSAGE CONTENT (what the user actually typed)
    AND returns the paired assistant solution

Retrieval strategy:
  1. Extract up to 5 high-signal keywords (stop-word filtered, ≥ 3 chars).
  2. SQL ILIKE search on messages WHERE sender_type='user', OR-joined keywords.
  3. Python scoring: count matched keywords per candidate; keep top-N.
  4. Single batched SQL: fetch the first AI message after each matched user
     message in the same conversation (one query, not N queries).
  5. Return (user_message, solution) pairs with a prompt-ready summary.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword extraction (shared logic with similar_issue_detector)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "i", "my", "me", "the", "a", "an", "is", "it", "to", "have", "has",
    "am", "are", "was", "be", "of", "in", "for", "and", "or", "but",
    "that", "this", "with", "on", "at", "can", "you", "your", "we",
    "not", "no", "do", "get", "got", "they", "them", "help", "please",
    "hi", "hey", "hello", "thanks", "thank", "just", "still", "again",
    "back", "into", "from", "about", "some", "any", "all", "there",
    "here", "then", "than", "so", "if", "as", "up", "out", "now",
    "issue", "problem", "issues", "problems",
})

_WORD_RE = re.compile(r"\b[a-z]{3,}\b")


def _extract_keywords(text: str) -> list[str]:
    """Return de-duplicated, stop-word filtered keywords (≥ 3 chars)."""
    if not text:
        return []
    words = _WORD_RE.findall(text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if w not in _STOP_WORDS and w not in seen:
            seen.add(w)
            result.append(w)
    return result


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RAGResult:
    """A matched (user issue, assistant solution) pair."""

    content: str          # the original user message text
    solution: str         # the assistant reply that followed (empty if none found)
    conversation_id: str  # which conversation it came from
    score: int            # number of query keywords matched
    created_at: Any = None


@dataclass
class RAGSearchResult:
    """Aggregated result from a RAGRepository search."""

    found: bool = False
    results: List[RAGResult] = field(default_factory=list)
    # Prompt-ready formatted block (injected into system message)
    summary: str = ""


# ---------------------------------------------------------------------------
# RAGRepository
# ---------------------------------------------------------------------------


class RAGRepository:
    """Retrieves similar past user messages from the messages table.

    Not a BaseRepository subclass — it performs a custom cross-table query
    rather than simple CRUD operations on a single model.
    """

    # Maximum keywords used for the SQL search (keeps the query compact)
    MAX_SEARCH_KEYWORDS = 5
    # Minimum number of keyword matches to include a result
    MIN_SCORE = 1

    async def find_similar_messages(
        self,
        db: Any,
        query: str,
        current_conversation_id: Optional[str] = None,
        limit: int = 3,
    ) -> RAGSearchResult:
        """Search message content for past issues similar to the query.

        Args:
            db:                       AsyncSession database session.
            query:                    Current user message text (the search query).
            current_conversation_id:  Exclude messages from this conversation.
            limit:                    Maximum number of results to return.

        Returns:
            RAGSearchResult — always valid, never raises.
        """
        try:
            return await self._search(db, query, current_conversation_id, limit)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAGRepository.find_similar_messages failed (non-fatal): %s", exc)
            return RAGSearchResult()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _search(
        self,
        db: Any,
        query: str,
        current_conversation_id: Optional[str],
        limit: int,
    ) -> RAGSearchResult:
        import json as _json

        from sqlalchemy import and_, or_, select

        from app.models.message import Message

        keywords = _extract_keywords(query)[: self.MAX_SEARCH_KEYWORDS]
        if len(keywords) < 2:
            # Too few meaningful keywords — skip retrieval to avoid noise
            return RAGSearchResult()

        # ── Step 1: find matching user messages ──────────────────────────────
        ilike_conditions = [Message.content.ilike(f"%{kw}%") for kw in keywords]

        user_filters = [
            Message.sender_type == "user",
            or_(*ilike_conditions),
        ]
        if current_conversation_id:
            user_filters.append(Message.conversation_id != current_conversation_id)

        user_stmt = (
            select(Message)
            .where(and_(*user_filters))
            .order_by(Message.created_at.desc())
            .limit(limit * 5)   # over-fetch for Python scoring
        )

        user_result = await db.execute(user_stmt)
        candidates = list(user_result.scalars().all())

        if not candidates:
            return RAGSearchResult()

        # ── Step 2: score and keep top-N ────────────────────────────────────
        query_kw_set = set(keywords)
        scored: list[tuple[int, Any]] = []
        for msg in candidates:
            msg_words = set(_extract_keywords(msg.content))
            score = len(query_kw_set & msg_words)
            if score >= self.MIN_SCORE:
                scored.append((score, msg))

        if not scored:
            return RAGSearchResult()

        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]

        # ── Step 3: fetch paired assistant responses (single batched query) ──
        # For each matched user message, we want the FIRST ai/agent message in
        # the same conversation that was created AFTER the user message.
        # One query: all AI messages in the matched conversations ordered by
        # created_at ASC; then we find the immediate successor in Python.
        conv_ids = list({msg.conversation_id for _, msg in top})
        # Use the earliest timestamp as a lower-bound so the query is tight
        earliest_ts = min(msg.created_at for _, msg in top)

        ai_stmt = (
            select(Message)
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.sender_type.in_(["ai", "agent"]),
                Message.created_at > earliest_ts,
            )
            .order_by(Message.created_at.asc())
        )
        ai_result = await db.execute(ai_stmt)
        ai_messages = list(ai_result.scalars().all())

        # Group AI messages by conversation for O(1) lookup
        ai_by_conv: dict[str, list[Any]] = {}
        for ai_msg in ai_messages:
            ai_by_conv.setdefault(ai_msg.conversation_id, []).append(ai_msg)

        # ── Step 4: build (user, solution) pairs ────────────────────────────
        rag_results: list[RAGResult] = []
        for score, user_msg in top:
            # Find first AI message after this user message in the same conv
            conv_ai = ai_by_conv.get(user_msg.conversation_id, [])
            next_ai = next(
                (m for m in conv_ai if m.created_at > user_msg.created_at),
                None,
            )

            solution = ""
            if next_ai:
                raw = (next_ai.content or "").strip()
                # Unwrap legacy JSON-wrapped AI content
                try:
                    parsed = _json.loads(raw)
                    raw = parsed.get("reply") or parsed.get("response") or raw
                except Exception:  # noqa: BLE001
                    pass
                solution = raw

            rag_results.append(RAGResult(
                content=user_msg.content,
                solution=solution,
                conversation_id=user_msg.conversation_id,
                score=score,
                created_at=user_msg.created_at,
            ))

        # ── Step 5: build WhatsApp-friendly prompt block ─────────────────────
        # Format: bullet per pair, short previews, solution only when present
        summary_lines: list[str] = []
        for r in rag_results:
            user_preview = r.content[:90] + ("…" if len(r.content) > 90 else "")
            line = f"• User: \"{user_preview}\""
            if r.solution:
                sol_preview = r.solution[:100] + ("…" if len(r.solution) > 100 else "")
                line += f"\n  Solution: \"{sol_preview}\""
            summary_lines.append(line)

        summary = "\n".join(summary_lines)

        pairs_with_solution = sum(1 for r in rag_results if r.solution)
        logger.info(
            "RAG: found %d pair(s) (%d with solution) for keywords %s",
            len(rag_results),
            pairs_with_solution,
            keywords[:3],
        )

        return RAGSearchResult(found=True, results=rag_results, summary=summary)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

rag_repository = RAGRepository()
