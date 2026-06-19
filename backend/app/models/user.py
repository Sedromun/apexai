from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base

if TYPE_CHECKING:
    from app.models.race_session import RaceSession


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    lang: Mapped[str] = mapped_column(String(8), default="ru", server_default="ru")
    # MVP keeps the tariff inline; a dedicated SUBSCRIPTION table arrives in the billing slice.
    plan: Mapped[str] = mapped_column(String(16), default="free", server_default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions: Mapped[list["RaceSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
