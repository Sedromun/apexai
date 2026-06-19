from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, Base, JSONVariant


class CoachReport(Base):
    """An LLM coach analysis for one lap. One cached report per lap (``lap_id`` unique)."""

    __tablename__ = "coach_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    lap_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("laps.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Structured layer-2 output (summary_text, top_mistakes, corner_notes, training_plan).
    summary: Mapped[dict[str, Any]] = mapped_column(JSONVariant)
    body: Mapped[str] = mapped_column(Text)  # rendered Russian markdown
    model: Mapped[str] = mapped_column(String(64))  # provider/model that produced it
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
