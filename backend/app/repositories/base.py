"""Generic async base repository."""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Provides common CRUD operations for a SQLAlchemy model.

    Subclasses must set ``model`` to the concrete model class.
    """

    model: Type[ModelType]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        """Retrieve a single record by primary key.

        Returns:
            The model instance or ``None`` if not found.
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieve a paginated list of all records."""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create and persist a new record.

        Args:
            obj_in: Dictionary of field values.

        Returns:
            The newly created and refreshed model instance.
        """
        instance = self.model(**obj_in)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(
        self, id: Any, obj_in: Dict[str, Any]
    ) -> Optional[ModelType]:
        """Update an existing record by primary key.

        Args:
            id: Primary key of the record.
            obj_in: Dictionary of fields to update (None values are skipped).

        Returns:
            The updated model instance or ``None`` if not found.
        """
        instance = await self.get(id)
        if instance is None:
            return None

        for field, value in obj_in.items():
            if value is not None:
                setattr(instance, field, value)

        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        """Delete a record by primary key.

        Returns:
            ``True`` if the record was deleted, ``False`` if not found.
        """
        instance = await self.get(id)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.flush()
        return True
