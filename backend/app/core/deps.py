from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AuthError
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.coach_service import CoachService
from app.services.lap_service import LapService
from app.storage.object_store import ObjectStore, get_object_store

DbDep = Annotated[AsyncSession, Depends(get_db)]
StoreDep = Annotated[ObjectStore, Depends(get_object_store)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbDep,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing bearer token")
    payload = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Invalid token subject") from exc
    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AuthError("User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(db)


def get_lap_service(db: DbDep, store: StoreDep) -> LapService:
    return LapService(db, store)


def get_coach_service(db: DbDep, store: StoreDep) -> CoachService:
    return CoachService(db, store)


def get_account_service(db: DbDep) -> AccountService:
    return AccountService(db)


def get_billing_service(db: DbDep) -> BillingService:
    return BillingService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
LapServiceDep = Annotated[LapService, Depends(get_lap_service)]
CoachServiceDep = Annotated[CoachService, Depends(get_coach_service)]
AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]
