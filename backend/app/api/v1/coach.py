import uuid

from fastapi import APIRouter

from app.core.deps import CoachServiceDep, CurrentUser
from app.schemas.coach import CoachAnalyzeRequest, CoachReportOut, TrajectoryLesson

router = APIRouter(tags=["coach"])


@router.get("/coach/trajectory", response_model=list[TrajectoryLesson])
async def trajectory(user: CurrentUser, service: CoachServiceDep) -> list[TrajectoryLesson]:
    """The user's learning trajectory — every coach lesson with lap/track context, oldest→newest."""
    return await service.get_trajectory(user)


@router.post("/coach/analyze", response_model=CoachReportOut, status_code=201)
async def analyze(
    body: CoachAnalyzeRequest, user: CurrentUser, service: CoachServiceDep
) -> CoachReportOut:
    """Generate (or return cached) AI coach report for a lap. Pro feature (1 free trial)."""
    return CoachReportOut.model_validate(await service.analyze(user, body.lap_id))


@router.get("/coach/reports/{report_id}", response_model=CoachReportOut)
async def get_report(
    report_id: uuid.UUID, user: CurrentUser, service: CoachServiceDep
) -> CoachReportOut:
    return CoachReportOut.model_validate(await service.get_report(user, report_id))


@router.get("/laps/{lap_id}/coach", response_model=CoachReportOut)
async def lap_report(
    lap_id: uuid.UUID, user: CurrentUser, service: CoachServiceDep
) -> CoachReportOut:
    """Existing coach report for a lap, or 404 if not analyzed yet."""
    return CoachReportOut.model_validate(await service.get_report_for_lap(user, lap_id))
