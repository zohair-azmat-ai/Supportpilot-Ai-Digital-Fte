"""Customer repository."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.customer import Customer, CustomerIdentifier
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Data access layer for the Customer and CustomerIdentifier models."""

    model = Customer

    async def get_by_user_id(self, user_id: str) -> Optional[Customer]:
        """Return the Customer linked to a given auth User ID, or None.

        Args:
            user_id: The primary key of the auth User record.

        Returns:
            The matching Customer instance, or ``None`` if not found.
        """
        result = await self.db.execute(
            select(Customer)
            .options(selectinload(Customer.identifiers))
            .where(Customer.user_id == user_id)
        )
        return result.scalars().first()

    async def get_by_identifier(
        self, channel: str, value: str
    ) -> Optional[Customer]:
        """Resolve a customer by their channel-specific identifier.

        Performs a JOIN between CustomerIdentifier and Customer, matching
        on the given channel and value pair.

        Args:
            channel: The communication channel (e.g., 'web', 'email', 'whatsapp').
            value: The identifier string on that channel (email address, phone, etc.).

        Returns:
            The matching Customer instance, or ``None`` if not found.
        """
        result = await self.db.execute(
            select(Customer)
            .options(selectinload(Customer.identifiers))
            .join(
                CustomerIdentifier,
                CustomerIdentifier.customer_id == Customer.id,
            )
            .where(
                CustomerIdentifier.channel == channel,
                CustomerIdentifier.value == value,
            )
        )
        return result.scalars().first()

    async def create_with_identifier(
        self,
        customer_data: dict,
        channel: str,
        value: str,
    ) -> Customer:
        """Create a Customer and an associated CustomerIdentifier in one transaction.

        The CustomerIdentifier created here is automatically marked as the primary
        identifier for the new customer.

        Args:
            customer_data: Dictionary of field values for the Customer record.
            channel: The communication channel for the initial identifier.
            value: The identifier string (email address, phone number, etc.).

        Returns:
            The newly created Customer instance (with identifier already flushed).
        """
        # Always generate external_id so the NOT NULL DB column is never NULL.
        # Callers that already include external_id in customer_data are not
        # overridden — setdefault only fills the gap when it is absent.
        customer_data.setdefault("external_id", str(uuid.uuid4()))
        # account_tier — DB column is NOT NULL; default to "free" if not supplied.
        customer_data.setdefault("account_tier", "free")
        # is_vip — DB column is NOT NULL; default to False if not supplied.
        customer_data.setdefault("is_vip", False)

        customer = self.model(**customer_data)
        self.db.add(customer)
        await self.db.flush()  # Ensure customer.id is available for the FK

        identifier = CustomerIdentifier(
            customer_id=customer.id,
            channel=channel,
            value=value,
            identifier=value,   # mirrors value — DB NOT NULL column
            is_primary=True,
        )
        self.db.add(identifier)
        await self.db.flush()
        await self.db.refresh(customer)
        return customer

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """Return a paginated list of all Customer records ordered by creation time.

        Args:
            skip: Number of records to skip (for pagination).
            limit: Maximum number of records to return.

        Returns:
            List of Customer instances.
        """
        result = await self.db.execute(
            select(Customer)
            .order_by(Customer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
