"""Authentication service."""

from __future__ import annotations

from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password, verify_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import SignupRequest
from jose import JWTError


class AuthService:
    """Handles user registration, login, and token resolution."""

    async def signup(self, db: AsyncSession, data: SignupRequest) -> User:
        """Register a new user.

        Args:
            db: Active database session.
            data: Validated signup payload.

        Returns:
            The newly created User instance.

        Raises:
            HTTPException 409: If the email is already registered.
        """
        repo = UserRepository(db)
        existing = await repo.get_by_email(data.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists",
            )

        user = await repo.create(
            {
                "name": data.name,
                "email": data.email,
                "password_hash": hash_password(data.password),
                "role": data.role or "customer",
            }
        )
        return user

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Tuple[User, str]:
        """Authenticate a user and return the user + JWT access token.

        Args:
            db: Active database session.
            email: User's email address.
            password: Plain-text password.

        Returns:
            Tuple of (User, access_token_string).

        Raises:
            HTTPException 401: If credentials are invalid.
            HTTPException 400: If the account is inactive.
        """
        repo = UserRepository(db)
        user = await repo.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is inactive. Please contact support.",
            )

        token = create_access_token(data={"sub": user.id})
        return user, token

    async def get_current_user(self, db: AsyncSession, token: str) -> User:
        """Resolve a JWT token to the associated user.

        Args:
            db: Active database session.
            token: Encoded JWT string.

        Returns:
            Authenticated User instance.

        Raises:
            HTTPException 401: If the token is invalid or the user is missing.
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

        repo = UserRepository(db)
        user = await repo.get(user_id)
        if user is None:
            raise credentials_exception
        return user


auth_service = AuthService()
