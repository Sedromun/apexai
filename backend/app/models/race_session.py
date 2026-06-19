from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base

if TYPE_CHECKING:
    from app.models.lap import Lap
    from app.models.user import User


class RaceSession(Base):
    """A practice/race session for one user. Track and car are denormalized strings
    for the MVP; dedicated TRACK/CAR dictionaries are a documented extension point."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    game: Mapped[str] = mapped_column(String(16))  # e.g. "f1_24", "f1_25"
    track: Mapped[str | None] = mapped_column(String(120), nullable=True)
    car_or_team: Mapped[str | None] = mapped_column(String(120), nullable=True)
    session_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weather: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Optional client-provided grouping key (one play session). Lets re-sent laps land in
    # the same session; when absent a new session is created per upload (refined in slice 2).
    client_session_uuid: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
    laps: Mapped[list["Lap"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Lap.recorded_at"
    )
