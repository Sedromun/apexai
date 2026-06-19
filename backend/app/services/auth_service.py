from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError
from app.core.security import (
    access_token_ttl_seconds,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import AccessToken, TokenPair


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def register(self, email: str, password: str) -> TokenPair:
        email = email.lower()
        if await self.users.get_by_email(email) is not None:
            raise ConflictError("Email already registered", code="email_taken")
        user = await self.users.create(email, hash_password(password))
        await self.db.commit()
        return self._issue(user)

    async def login(self, email: str, password: str) -> TokenPair:
        email = email.lower()
        user = await self.users.get_by_email(email)
        # verify_password is called even when user is None would skip — but we still want a
        # constant-ish path; argon2 verify dominates timing, so a missing user is acceptable.
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password", code="invalid_credentials")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await self.db.commit()
        return self._issue(user)

    async def refresh(self, refresh_token: str) -> AccessToken:
        payload = decode_token(refresh_token, expected_type="refresh")
        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise AuthError("Invalid token subject") from exc
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise AuthError("User not found")
        return AccessToken(
            access_token=create_access_token(user.id),
            expires_in=access_token_ttl_seconds(),
        )

    def _issue(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            expires_in=access_token_ttl_seconds(),
        )
