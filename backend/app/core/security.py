"""Security utilities: password hashing and JWT token management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing  (bcrypt directly — no passlib wrapper)
#
# passlib 1.7.4 is incompatible with bcrypt >= 4.0 (the bcrypt.__about__
# module was removed in 4.0, causing passlib to crash even on short passwords).
# Using the bcrypt package directly avoids the entire compatibility layer.
# ---------------------------------------------------------------------------

# bcrypt processes at most 72 bytes of password.  We truncate explicitly so
# that hash_password and verify_password always operate on the same byte slice.
_BCRYPT_MAX_BYTES = 72
_BCRYPT_ROUNDS = 12  # NIST-recommended work factor (adjust up over time)


def _normalise_password(password: str) -> bytes:
    """Encode password to UTF-8 and truncate to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password* as a UTF-8 string."""
    hashed: bytes = _bcrypt.hashpw(
        _normalise_password(password),
        _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    )
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches the stored *hashed_password*."""
    return _bcrypt.checkpw(
        _normalise_password(plain_password),
        hashed_password.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload data to encode into the token.
        expires_delta: Optional custom expiry duration. Defaults to
            ``ACCESS_TOKEN_EXPIRE_MINUTES`` from settings.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        JWTError: If the token is invalid or expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
