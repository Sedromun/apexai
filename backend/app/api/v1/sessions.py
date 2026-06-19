import uuid

from fastapi import APIRouter

from app.core.deps import CurrentUser, LapServiceDep
from app.schemas.lap import LapSummary, SessionSummary

router = APIRouter(tags=["sessions"])


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(user: CurrentUser, service: LapServiceDep) -> list[SessionSummary]:
    return await service.list_sessions(user)


@router.get("/sessions/{session_id}/laps", response_model=list[LapSummary])
async def session_laps(
    session_id: uuid.UUID, user: CurrentUser, service: LapServiceDep
) -> list[LapSummary]:
    return await service.list_session_laps(user, session_id)
