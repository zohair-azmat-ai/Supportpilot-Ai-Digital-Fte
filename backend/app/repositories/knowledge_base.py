"""KnowledgeBase repository."""

from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import or_, select

from app.models.knowledge_base import KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """Data access layer for the KnowledgeBase model."""

    model = KnowledgeBase

    async def search(self, query: str, limit: int = 5) -> List[KnowledgeBase]:
        """Search active articles using case-insensitive keyword matching.

        The query string is split into individual words. An article is returned
        if ANY word from the query appears in the title, content, or tags fields.
        Only articles where ``is_active=True`` are considered.

        This is a lightweight SQL LIKE-based fallback. Phase 2 will replace or
        supplement this with pgvector similarity search using the ``embedding``
        field.

        Args:
            query: Free-text search string; will be tokenised on whitespace.
            limit: Maximum number of matching articles to return.

        Returns:
            List of matching KnowledgeBase instances ordered by title.
        """
        words = [w.strip() for w in query.split() if w.strip()]
        if not words:
            return []

        # Build an OR clause: any column contains any query word
        conditions = []
        for word in words:
            pattern = f"%{word}%"
            conditions.append(KnowledgeBase.content.ilike(pattern))
            conditions.append(KnowledgeBase.tags.ilike(pattern))

        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                KnowledgeBase.is_active == True,  # noqa: E712
                or_(*conditions),
            )
            .order_by(KnowledgeBase.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_with_scores(
        self, query: str, limit: int = 5
    ) -> List[Tuple[KnowledgeBase, float]]:
        """Search articles and return each with a relevance confidence score (0–1).

        Confidence = (number of query words found in the article) / (total query words).
        Results are ordered by confidence descending.

        Args:
            query: Free-text search string.
            limit: Maximum results to return.

        Returns:
            List of (KnowledgeBase, confidence_score) tuples, best match first.
        """
        words = [w.strip().lower() for w in query.split() if w.strip()]
        if not words:
            return []

        # First fetch candidates via SQL LIKE (fast filter)
        candidates = await self.search(query, limit=limit * 3)

        if not candidates:
            return []

        # Score each candidate in Python — count matched words in search string
        scored: list[tuple[KnowledgeBase, float]] = []
        for article in candidates:
            search_text = article.to_search_string()
            matched = sum(1 for w in words if w in search_text)
            confidence = matched / len(words)
            scored.append((article, round(confidence, 3)))

        # Sort by score descending and return top-limit
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    async def get_by_category(
        self, category: str, limit: int = 20
    ) -> List[KnowledgeBase]:
        """Return active articles belonging to a specific category.

        Args:
            category: Category identifier string (e.g., 'billing', 'technical').
            limit: Maximum number of articles to return.

        Returns:
            List of KnowledgeBase instances ordered by title.
        """
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(
                KnowledgeBase.category == category,
                KnowledgeBase.is_active == True,  # noqa: E712
            )
            .order_by(KnowledgeBase.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_article(self, data_dict: dict) -> KnowledgeBase:
        """Persist a new knowledge base article.

        Args:
            data_dict: Dictionary of field values for the KnowledgeBase record.

        Returns:
            The newly created KnowledgeBase instance.
        """
        return await self.create(data_dict)

    async def get_all_active(
        self, skip: int = 0, limit: int = 100
    ) -> List[KnowledgeBase]:
        """Return a paginated list of active articles ordered by title.

        Args:
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.

        Returns:
            List of active KnowledgeBase instances.
        """
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.is_active == True)  # noqa: E712
            .order_by(KnowledgeBase.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
