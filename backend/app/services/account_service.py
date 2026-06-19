from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.repositories.coach_repo import CoachReportRepository
from app.repositories.lap_repo import LapRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.schemas.account import AccountLimits, AccountOut, AccountUsage, SubscriptionOut


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.laps = LapRepository(db)
        self.reports = CoachReportRepository(db)
        self.subs = SubscriptionRepository(db)

    async def overview(self, user: User) -> AccountOut:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        laps_this_month = await self.laps.count_for_user_since(user.id, month_start)
        ai_reports_used = await self.reports.count_for_user(user.id)
        sub = await self.subs.get_active_for_user(user.id)

        return AccountOut(
            id=user.id,
            email=user.email,
            lang=user.lang,
            plan=user.plan,
            limits=AccountLimits(
                free_monthly_lap_limit=settings.free_monthly_lap_limit,
                free_ai_trial=settings.free_ai_trial,
            ),
            usage=AccountUsage(
                laps_this_month=laps_this_month, ai_reports_used=ai_reports_used
            ),
            subscription=SubscriptionOut.model_validate(sub) if sub else None,
        )
