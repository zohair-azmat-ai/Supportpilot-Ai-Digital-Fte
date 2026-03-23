"""User repository."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for the User model."""

    model = User

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email address.

        Returns:
            The User instance or ``None`` if not found.
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Return a paginated list of all users ordered by creation date."""
        result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count_users(self) -> int:
        """Return the total count of registered users."""
        result = await self.db.execute(select(func.count()).select_from(User))
        return result.scalar_one()
