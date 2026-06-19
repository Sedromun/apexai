from fastapi import APIRouter

from app.core.deps import AccountServiceDep, CurrentUser
from app.schemas.account import AccountOut

router = APIRouter(tags=["account"])


@router.get("/me", response_model=AccountOut)
async def me(user: CurrentUser, service: AccountServiceDep) -> AccountOut:
    """Profile + tariff + current usage (laps this month, AI reports used)."""
    return await service.overview(user)
