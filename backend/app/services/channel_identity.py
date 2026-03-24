"""
Cross-channel customer identity resolution service.

Responsibility
--------------
Given a channel (web / email / whatsapp) and a channel-specific identifier
(email address or phone number), this service:

  1. Looks up an existing CustomerIdentifier → Customer → User.
  2. If not found, creates a new User + Customer + CustomerIdentifier atomically.

This ensures that:
  - The same real-world person appearing on multiple channels (e.g. email then
    WhatsApp) is represented by ONE Customer record.
  - All conversations and tickets across channels link to the same user_id,
    enabling the AI agent to retrieve the full cross-channel support history.

Identity mapping
----------------
  Channel   | Identifier value        | User email
  ----------|-------------------------|-------------------------------------------
  web       | email address           | the actual email
  email     | email address           | the actual email
  whatsapp  | E.164 phone (+1XXXXXXX) | <digits>@whatsapp.supportpilot.internal
"""

from __future__ import annotations

import logging
import secrets
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.repositories.customer import CustomerRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


def _normalize_identifier(channel: str, value: str) -> str:
    """Canonicalize identifiers before looking up customer identities."""
    cleaned = value.strip()
    if channel in ("web", "email"):
        return cleaned.lower()
    if channel == "whatsapp":
        cleaned = cleaned.replace("whatsapp:", "").strip()
        digits = re.sub(r"[^\d+]", "", cleaned)
        return digits if digits.startswith("+") else f"+{digits}"
    return cleaned


class ChannelIdentityService:
    """Resolve or create a User from a channel + identifier pair."""

    async def resolve_or_create(
        self,
        db: AsyncSession,
        channel: str,
        identifier_value: str,
        display_name: str,
        *,
        company: Optional[str] = None,
    ) -> User:
        """Return the User that owns this channel identity, creating if needed.

        Args:
            db               : Active database session.
            channel          : 'web', 'email', or 'whatsapp'.
            identifier_value : Email address for web/email; E.164 phone for whatsapp.
            display_name     : Human-readable name (used when creating new records).
            company          : Optional company name for the customer profile.

        Returns:
            The matching or newly created User.
        """
        customer_repo = CustomerRepository(db)
        user_repo = UserRepository(db)
        identifier_value = _normalize_identifier(channel, identifier_value)

        # 1. Try to resolve via CustomerIdentifier
        customer = await customer_repo.get_by_identifier(channel, identifier_value)
        if customer and customer.user_id:
            user = await user_repo.get(customer.user_id)
            if user:
                logger.debug(
                    "Resolved existing user via CustomerIdentifier | channel=%s value=%s user=%s",
                    channel,
                    identifier_value,
                    user.id,
                )
                return user

        # 2. Determine the email to use for the User record
        if channel in ("web", "email"):
            user_email = identifier_value
        else:
            # WhatsApp: synthetic email — not a real address, just a system key
            digits = identifier_value.lstrip("+")
            user_email = f"{digits}@whatsapp.supportpilot.internal"

        # 3. Try to find an existing User by email (might exist without a CustomerIdentifier)
        user = await user_repo.get_by_email(user_email)

        if user is None:
            # 4. Create a new User
            user = await user_repo.create({
                "name": display_name,
                "email": user_email,
                "password_hash": hash_password(secrets.token_urlsafe(32)),
                "role": "customer",
            })
            logger.info(
                "Created new user for channel | channel=%s value=%s user_id=%s",
                channel,
                identifier_value,
                user.id,
            )

        # 5. Ensure a Customer record and CustomerIdentifier exist
        existing_customer = await customer_repo.get_by_user_id(user.id)
        if existing_customer is None:
            existing_customer = await customer_repo.create_with_identifier(
                customer_data={
                    "user_id": user.id,
                    "name": display_name,
                    "company": company,
                    "is_active": True,
                },
                channel=channel,
                value=identifier_value,
            )
            logger.info(
                "Created Customer + CustomerIdentifier | channel=%s customer_id=%s",
                channel,
                existing_customer.id,
            )
        else:
            # Ensure the identifier exists (may be missing for older records)
            existing_id = await customer_repo.get_by_identifier(channel, identifier_value)
            if existing_id is None:
                from app.models.customer import CustomerIdentifier
                new_ident = CustomerIdentifier(
                    customer_id=existing_customer.id,
                    channel=channel,
                    value=identifier_value,
                    is_primary=False,
                )
                db.add(new_ident)
                await db.flush()
                logger.info(
                    "Added CustomerIdentifier to existing customer | channel=%s customer_id=%s",
                    channel,
                    existing_customer.id,
                )

        return user


# Type import only used in annotation
from typing import Optional  # noqa: E402  (must come after class body for Python <3.10 compat)

# Module-level singleton
channel_identity_service = ChannelIdentityService()
