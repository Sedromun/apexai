from fastapi import APIRouter

from app.core.deps import AuthServiceDep
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(body: RegisterRequest, service: AuthServiceDep) -> TokenPair:
    return await service.register(body.email, body.password)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, service: AuthServiceDep) -> TokenPair:
    return await service.login(body.email, body.password)


@router.post("/refresh", response_model=AccessToken)
async def refresh(body: RefreshRequest, service: AuthServiceDep) -> AccessToken:
    return await service.refresh(body.refresh_token)
