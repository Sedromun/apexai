from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, JSONVariant

if TYPE_CHECKING:
    from app.models.race_session import RaceSession
    from app.models.telemetry_trace import TelemetryTrace


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    # Client-generated idempotency key: re-sending a queued lap must not duplicate it.
    client_lap_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lap_time_ms: Mapped[int] = mapped_column(Integer)
    valid: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    # Layer-1 deterministic metrics (corner segmentation, deltas). Filled by the metrics slice.
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["RaceSession"] = relationship(back_populates="laps")
    trace: Mapped["TelemetryTrace | None"] = relationship(
        back_populates="lap", cascade="all, delete-orphan", uselist=False
    )

    @property
    def has_metrics(self) -> bool:
        return self.metrics is not None
