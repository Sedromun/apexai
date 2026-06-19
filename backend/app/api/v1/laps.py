import uuid
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import ValidationError

from app.core.deps import CurrentUser, LapServiceDep
from app.core.errors import ValidationAppError, simplify_validation_errors
from app.schemas.lap import LapCompare, LapDetail, LapListItem, LapMeta, LapSummary
from app.schemas.track import ReferenceCompare

router = APIRouter(tags=["laps"])


@router.post("/laps", response_model=LapSummary, status_code=201)
async def upload_lap(
    user: CurrentUser,
    service: LapServiceDep,
    meta: str = Form(..., description="JSON-encoded LapMeta"),
    trace: UploadFile = File(..., description="gzip-compressed lap-trace/1 JSON"),
) -> LapSummary:
    try:
        meta_obj = LapMeta.model_validate_json(meta)
    except ValidationError as exc:
        raise ValidationAppError(
            "Invalid lap metadata",
            code="invalid_meta",
            details=simplify_validation_errors(exc.errors()),
        ) from exc
    blob = await trace.read()
    lap = await service.ingest(user, meta_obj, blob)
    return LapSummary.model_validate(lap)


@router.get("/laps", response_model=list[LapListItem])
async def list_laps(user: CurrentUser, service: LapServiceDep) -> list[LapListItem]:
    """All of the caller's laps (newest first) — for pickers and lists."""
    return await service.list_user_laps(user)


@router.get("/laps/compare", response_model=LapCompare)
async def compare_laps(
    a: uuid.UUID, b: uuid.UUID, user: CurrentUser, service: LapServiceDep
) -> LapCompare:
    """Delta-time-by-distance comparison of two of the caller's laps (a = self, b = reference)."""
    return await service.compare(user, a, b)


@router.get("/laps/{lap_id}", response_model=LapDetail)
async def lap_detail(lap_id: uuid.UUID, user: CurrentUser, service: LapServiceDep) -> LapDetail:
    return await service.get_lap_detail(user, lap_id)


@router.get("/laps/{lap_id}/trace")
async def lap_trace(
    lap_id: uuid.UUID, user: CurrentUser, service: LapServiceDep
) -> dict[str, Any]:
    """Decompressed lap-trace/1 (columnar channels) for the web charts."""
    return await service.get_lap_trace(user, lap_id)


@router.get("/laps/{lap_id}/reference-compare", response_model=ReferenceCompare)
async def reference_compare(
    lap_id: uuid.UUID, user: CurrentUser, service: LapServiceDep
) -> ReferenceCompare:
    """Delta of the caller's lap vs the modeled 'ideal lap' for its track."""
    return await service.compare_reference(user, lap_id)
