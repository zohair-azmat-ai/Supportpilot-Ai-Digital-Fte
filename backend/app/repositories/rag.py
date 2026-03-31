"""
RAGRepository — message-content based similar issue retrieval.

Searches the messages table for past user messages whose content overlaps
with the current query.  This is the retrieval half of a lightweight RAG
pipeline: no embeddings, no vector store — pure keyword matching in SQL.

How it differs from SimilarIssueDetector:
  - SimilarIssueDetector compares ticket TITLES/DESCRIPTIONS (structured data)
  - RAGRepository compares raw MESSAGE CONTENT (what the user actually typed)

The two signals are complementary: ticket similarity catches known issue patterns;
message-content similarity catches phrasing and wording the user is repeating.

Retrieval strategy:
  1. Extract up to 5 high-signal keywords from the query (stop-word filtered,
     3+ character alphabetic words).
  2. Search messages with ILIKE patterns — one condition per keyword, OR-joined.
  3. Filter: sender_type='user', exclude current conversation.
  4. Score each candidate in Python by counting matched keywords.
  5. Return top-N by score (descending), ties broken by recency.
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
    """A single retrieved message that matches the query."""

    content: str          # the original user message text
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
        from sqlalchemy import and_, or_, select

        from app.models.message import Message

        keywords = _extract_keywords(query)[: self.MAX_SEARCH_KEYWORDS]
        if len(keywords) < 2:
            # Too few meaningful keywords — skip retrieval to avoid noise
            return RAGSearchResult()

        # Build OR-joined ILIKE conditions — one per keyword
        ilike_conditions = [Message.content.ilike(f"%{kw}%") for kw in keywords]

        filters = [
            Message.sender_type == "user",
            or_(*ilike_conditions),
        ]
        if current_conversation_id:
            filters.append(Message.conversation_id != current_conversation_id)

        stmt = (
            select(Message)
            .where(and_(*filters))
            .order_by(Message.created_at.desc())
            # Over-fetch so Python scoring can pick the best matches
            .limit(limit * 5)
        )

        result = await db.execute(stmt)
        candidates = list(result.scalars().all())

        if not candidates:
            return RAGSearchResult()

        # Score each candidate by keyword match count, then pick top-N
        query_kw_set = set(keywords)
        scored: list[tuple[int, Any]] = []
        for msg in candidates:
            msg_words = set(_extract_keywords(msg.content))
            score = len(query_kw_set & msg_words)
            if score >= self.MIN_SCORE:
                scored.append((score, msg))

        if not scored:
            return RAGSearchResult()

        # Sort by score descending (recency already handled by SQL ORDER BY)
        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]

        rag_results = [
            RAGResult(
                content=msg.content,
                conversation_id=msg.conversation_id,
                score=score,
                created_at=msg.created_at,
            )
            for score, msg in top
        ]

        # Build a concise, prompt-ready summary block
        summary_lines: list[str] = []
        for r in rag_results:
            preview = r.content[:120]
            if len(r.content) > 120:
                preview += "…"
            summary_lines.append(f"  • \"{preview}\" (matched {r.score} keyword(s))")

        summary = "\n".join(summary_lines)
        logger.info(
            "RAG: found %d similar message(s) for query keywords %s",
            len(rag_results),
            keywords[:3],
        )

        return RAGSearchResult(found=True, results=rag_results, summary=summary)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

rag_repository = RAGRepository()
