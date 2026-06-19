from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# MVP scope: F1 24 / F1 25 only. The desktop client sends "f1_24" or "f1_25".
GAME_PATTERN = r"^f1_(24|25)$"


class LapMeta(BaseModel):
    """Metadata part of ``POST /laps`` (sent as a JSON string beside the gzipped trace)."""

    client_lap_uuid: str = Field(min_length=8, max_length=64)
    client_session_uuid: str | None = Field(default=None, max_length=64)
    game: str = Field(pattern=GAME_PATTERN)
    track: str | None = Field(default=None, max_length=120)
    car_or_team: str | None = Field(default=None, max_length=120)
    session_type: str | None = Field(default=None, max_length=40)
    weather: str | None = Field(default=None, max_length=40)
    lap_time_ms: int = Field(gt=0, lt=3_600_000)
    valid: bool = True
    recorded_at: datetime
    sample_count: int = Field(ge=0, le=200_000)


class LapSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    lap_time_ms: int
    valid: bool
    sample_count: int
    recorded_at: datetime
    has_metrics: bool


class LapListItem(BaseModel):
    """Flat lap entry for pickers/lists (carries denormalized session labels)."""

    id: uuid.UUID
    session_id: uuid.UUID
    game: str
    track: str | None
    car_or_team: str | None
    lap_time_ms: int
    valid: bool
    recorded_at: datetime


class SessionSummary(BaseModel):
    id: uuid.UUID
    game: str
    track: str | None
    car_or_team: str | None
    session_type: str | None
    started_at: datetime
    lap_count: int
    best_lap_time_ms: int | None


class TraceMeta(BaseModel):
    schema_version: str
    hz: int
    points: int
    size_bytes: int


class LapDetail(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    game: str
    track: str | None
    car_or_team: str | None
    lap_time_ms: int
    valid: bool
    sample_count: int
    recorded_at: datetime
    has_metrics: bool
    metrics: dict[str, Any] | None
    trace: TraceMeta | None
    reference_lap_id: uuid.UUID | None = None
    # Modeled 'ideal lap' available for this track (label/kind/lap_time_ms), if any.
    track_reference: dict[str, Any] | None = None


class CompareLapRef(BaseModel):
    id: uuid.UUID
    lap_time_ms: int
    track: str | None


class LapCompare(BaseModel):
    """Delta-time-by-distance comparison of lap ``a`` (self) against lap ``b`` (reference)."""

    a: CompareLapRef
    b: CompareLapRef
    distance_m: list[float]
    delta_s: list[float]
    total_delta_s: float
    corners: list[dict[str, Any]]
