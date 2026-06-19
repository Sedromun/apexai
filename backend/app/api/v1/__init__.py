from fastapi import APIRouter

from app.api.v1 import account, auth, billing, coach, health, laps, sessions, tracks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(sessions.router)
api_router.include_router(laps.router)
api_router.include_router(tracks.router)
api_router.include_router(coach.router)
api_router.include_router(billing.router)

__all__ = ["api_router"]
