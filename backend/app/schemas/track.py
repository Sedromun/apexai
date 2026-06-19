from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TrackCorner(BaseModel):
    n: int
    name: str


class TrackMap(BaseModel):
    view_box: str
    path: str
    start: dict[str, float]


class TrackReferenceMeta(BaseModel):
    """Describes the modeled 'ideal lap' available for a track."""

    label: str
    kind: str  # "modeled" (or "real" once a captured lap is designated)
    lap_time_ms: int
    max_speed_kmh: float


class TrackInfo(BaseModel):
    name: str
    length_m: int | None
    drs_zones: int | None
    record: str | None
    corner_count: int
    corners: list[TrackCorner]
    map: TrackMap | None
    reference: TrackReferenceMeta | None


class ReferenceCompare(BaseModel):
    """Delta-time-by-distance of the caller's lap against the track's modeled ideal lap."""

    track: str
    reference_label: str
    reference_lap_time_ms: int
    self_lap_time_ms: int
    distance_m: list[float]
    delta_s: list[float]
    total_delta_s: float
    corners: list[dict[str, Any]]
