"""Password hashing (argon2) and JWT issue/verify helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings
from app.core.errors import AuthError

_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Malformed hash, etc. — treat as a failed verification, never raise to the caller.
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def _create_token(subject: uuid.UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.access_token_ttl_minutes))


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.refresh_token_ttl_days))


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises AuthError on any problem."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthError(f"Expected a {expected_type} token")
    return payload


def access_token_ttl_seconds() -> int:
    return settings.access_token_ttl_minutes * 60
