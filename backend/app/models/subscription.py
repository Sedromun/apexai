from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, Base


class Subscription(Base):
    """A user's paid subscription. Created ``pending`` at checkout, flipped to ``active``
    by the billing webhook. The authoritative tariff lives on ``User.plan``; this table is
    the billing history / state behind it."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan: Mapped[str] = mapped_column(String(32))  # "pro_monthly" | "pro_yearly"
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|active|canceled
    provider: Mapped[str] = mapped_column(String(32))  # "stub" | "yookassa" | "cloudpayments"
    provider_ref: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
