"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_token

# Re-export get_db so dependants can import from a single location
__all__ = ["get_db", "get_current_user", "get_current_active_user", "require_admin"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Resolve the JWT token to the authenticated User model.

    Raises:
        HTTPException 401: If the token is missing, invalid, or the user
            does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Import here to avoid circular dependency at module load time
    from app.repositories.user import UserRepository

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    """Ensure the authenticated user has an active account.

    Raises:
        HTTPException 400: If the account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    return current_user


async def require_admin(
    current_user=Depends(get_current_active_user),
):
    """Restrict access to admin users only.

    Raises:
        HTTPException 403: If the user does not have the admin role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
