from typing import Any

from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.core.errors import NotFoundError
from app.schemas.track import TrackInfo, TrackReferenceMeta
from app.services import track_catalog

router = APIRouter(tags=["tracks"])


@router.get("/tracks/{track}", response_model=TrackInfo)
async def track_info(track: str, user: CurrentUser) -> TrackInfo:
    """Static metadata for a track: corners, circuit-map geometry, lap record."""
    data = track_catalog.get_track(track)
    if data is None:
        raise NotFoundError("Track not found", code="track_not_found")
    ref = track_catalog.reference_meta(track)
    return TrackInfo(
        name=data["name"],
        length_m=data.get("length_m"),
        drs_zones=data.get("drs_zones"),
        record=data.get("record"),
        corner_count=data["corner_count"],
        corners=data["corners"],
        map=data.get("map"),
        reference=TrackReferenceMeta.model_validate(ref) if ref else None,
    )


@router.get("/tracks/{track}/reference")
async def track_reference(track: str, user: CurrentUser) -> dict[str, Any]:
    """The modeled 'ideal lap' trace (lap-trace/1) to overlay, plus its metadata."""
    trace = track_catalog.reference_trace(track)
    if trace is None:
        raise NotFoundError("No reference lap for this track", code="reference_not_found")
    return {"trace": trace.to_dict(), "meta": track_catalog.reference_meta(track)}
