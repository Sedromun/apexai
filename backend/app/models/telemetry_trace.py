from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base

if TYPE_CHECKING:
    from app.models.lap import Lap


class TelemetryTrace(Base):
    """Pointer to the raw lap trace stored in object storage (one row per lap).

    The heavy ~60 Hz sample arrays never touch Postgres — only this metadata does.
    """

    __tablename__ = "telemetry_traces"

    lap_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("laps.id", ondelete="CASCADE"), primary_key=True
    )
    storage_key: Mapped[str] = mapped_column(String(512))
    hz: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_encoding: Mapped[str] = mapped_column(String(16), default="gzip")
    schema_version: Mapped[str] = mapped_column(String(32), default="lap-trace/1")

    lap: Mapped["Lap"] = relationship(back_populates="trace")
