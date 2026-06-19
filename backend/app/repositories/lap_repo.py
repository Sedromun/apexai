from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lap import Lap
from app.models.race_session import RaceSession


class LapRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_client_uuid(self, client_lap_uuid: str) -> Lap | None:
        result = await self.db.execute(
            select(Lap).where(Lap.client_lap_uuid == client_lap_uuid)
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, lap_id: uuid.UUID, user_id: uuid.UUID) -> Lap | None:
        """Load a lap only if it belongs to ``user_id`` (ownership enforced in SQL)."""
        result = await self.db.execute(
            select(Lap)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(Lap.id == lap_id, RaceSession.user_id == user_id)
            .options(selectinload(Lap.session), selectinload(Lap.trace))
        )
        return result.scalar_one_or_none()

    async def list_for_session(self, session_id: uuid.UUID) -> Sequence[Lap]:
        result = await self.db.execute(
            select(Lap).where(Lap.session_id == session_id).order_by(Lap.recorded_at)
        )
        return result.scalars().all()

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 300) -> Sequence[Lap]:
        result = await self.db.execute(
            select(Lap)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(RaceSession.user_id == user_id)
            .options(selectinload(Lap.session))
            .order_by(Lap.recorded_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def count_for_user_since(self, user_id: uuid.UUID, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Lap.id))
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(RaceSession.user_id == user_id, Lap.created_at >= since)
        )
        return int(result.scalar_one())

    async def get_best_lap_for_track(
        self,
        user_id: uuid.UUID,
        game: str,
        track: str | None,
        *,
        exclude_lap_id: uuid.UUID | None = None,
    ) -> Lap | None:
        """Fastest valid lap for the user on the same game+track (the overlay reference)."""
        stmt = (
            select(Lap)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(
                RaceSession.user_id == user_id,
                RaceSession.game == game,
                Lap.valid.is_(True),
                RaceSession.track.is_(None) if track is None else RaceSession.track == track,
            )
            .order_by(Lap.lap_time_ms.asc())
            .limit(1)
            .options(selectinload(Lap.trace))
        )
        if exclude_lap_id is not None:
            stmt = stmt.where(Lap.id != exclude_lap_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        client_lap_uuid: str,
        lap_time_ms: int,
        valid: bool,
        sample_count: int,
        recorded_at: datetime,
        lap_id: uuid.UUID | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> Lap:
        lap = Lap(
            id=lap_id or uuid.uuid4(),
            session_id=session_id,
            client_lap_uuid=client_lap_uuid,
            lap_time_ms=lap_time_ms,
            valid=valid,
            sample_count=sample_count,
            recorded_at=recorded_at,
            metrics=metrics,
        )
        self.db.add(lap)
        await self.db.flush()
        return lap
