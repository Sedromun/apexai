from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lap import Lap
from app.models.race_session import RaceSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: uuid.UUID) -> RaceSession | None:
        return await self.db.get(RaceSession, session_id)

    async def get_by_client_uuid(self, client_session_uuid: str) -> RaceSession | None:
        result = await self.db.execute(
            select(RaceSession).where(RaceSession.client_session_uuid == client_session_uuid)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        game: str,
        track: str | None,
        car_or_team: str | None,
        session_type: str | None,
        weather: str | None,
        client_session_uuid: str | None,
        started_at: datetime,
    ) -> RaceSession:
        session = RaceSession(
            id=uuid.uuid4(),
            user_id=user_id,
            game=game,
            track=track,
            car_or_team=car_or_team,
            session_type=session_type,
            weather=weather,
            client_session_uuid=client_session_uuid,
            started_at=started_at,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def list_for_user_with_aggregates(
        self, user_id: uuid.UUID
    ) -> Sequence[Row[tuple[RaceSession, int, int | None]]]:
        """Sessions newest-first, each with lap count and best *valid* lap time."""
        best_valid = func.min(case((Lap.valid.is_(True), Lap.lap_time_ms), else_=None))
        stmt = (
            select(RaceSession, func.count(Lap.id), best_valid)
            .outerjoin(Lap, Lap.session_id == RaceSession.id)
            .where(RaceSession.user_id == user_id)
            .group_by(RaceSession.id)
            .order_by(RaceSession.started_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.all()
