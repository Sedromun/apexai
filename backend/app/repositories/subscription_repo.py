from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, *, user_id: uuid.UUID, plan: str, status: str, provider: str, provider_ref: str
    ) -> Subscription:
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan=plan,
            status=status,
            provider=provider,
            provider_ref=provider_ref,
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def get_by_provider_ref(self, provider_ref: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.provider_ref == provider_ref)
        )
        return result.scalar_one_or_none()

    async def get_active_for_user(self, user_id: uuid.UUID) -> Subscription | None:
        """Latest active subscription, or the latest of any status for display."""
        active = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        found = active.scalar_one_or_none()
        if found is not None:
            return found
        latest = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return latest.scalar_one_or_none()

    async def activate(self, sub: Subscription, period_end: datetime) -> None:
        sub.status = "active"
        sub.current_period_end = period_end
        await self.db.flush()

    async def cancel(self, sub: Subscription) -> None:
        sub.status = "canceled"
        await self.db.flush()
