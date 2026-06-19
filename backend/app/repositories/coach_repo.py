from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach_report import CoachReport
from app.models.lap import Lap
from app.models.race_session import RaceSession


class CoachReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_lap(self, lap_id: uuid.UUID) -> CoachReport | None:
        result = await self.db.execute(
            select(CoachReport).where(CoachReport.lap_id == lap_id)
        )
        return result.scalar_one_or_none()

    async def get_for_user(self, report_id: uuid.UUID, user_id: uuid.UUID) -> CoachReport | None:
        result = await self.db.execute(
            select(CoachReport)
            .join(Lap, CoachReport.lap_id == Lap.id)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(CoachReport.id == report_id, RaceSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(CoachReport.id))
            .join(Lap, CoachReport.lap_id == Lap.id)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(RaceSession.user_id == user_id)
        )
        return int(result.scalar_one())

    async def get_previous_for_track(
        self,
        user_id: uuid.UUID,
        game: str,
        track: str | None,
        before_recorded_at: datetime,
        exclude_lap_id: uuid.UUID,
    ) -> CoachReport | None:
        """Most recent prior coach report for this user on the same game+track — the previous
        'lesson', used to review the homework and build a learning progression."""
        stmt = (
            select(CoachReport)
            .join(Lap, CoachReport.lap_id == Lap.id)
            .join(RaceSession, Lap.session_id == RaceSession.id)
            .where(
                RaceSession.user_id == user_id,
                RaceSession.game == game,
                RaceSession.track.is_(None) if track is None else RaceSession.track == track,
                Lap.id != exclude_lap_id,
                Lap.recorded_at < before_recorded_at,
            )
            .order_by(Lap.recorded_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, *, lap_id: uuid.UUID, summary: dict[str, Any], body: str, model: str
    ) -> CoachReport:
        report = CoachReport(
            id=uuid.uuid4(), lap_id=lap_id, summary=summary, body=body, model=model
        )
        self.db.add(report)
        await self.db.flush()
        return report
