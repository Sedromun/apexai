from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.provider import PaymentProvider, get_payment_provider
from app.core.config import settings
from app.core.errors import ValidationAppError
from app.models.user import User
from app.repositories.subscription_repo import SubscriptionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.billing import PlanOut, SubscribeOut

logger = logging.getLogger(__name__)

# Static plan catalogue. Prices are placeholders for the CIS market (RUB).
PLANS: list[PlanOut] = [
    PlanOut(
        id="free",
        title="Free",
        price_rub=0,
        period=None,
        features=["До 30 кругов в месяц", "Графики телеметрии", "Сравнение со своим лучшим", "1 пробный AI-разбор"],
    ),
    PlanOut(
        id="pro_monthly",
        title="Pro — месяц",
        price_rub=690,
        period="month",
        features=["Безлимит кругов", "Безлимитный AI-разбор тренера", "Полная история и прогресс"],
    ),
    PlanOut(
        id="pro_yearly",
        title="Pro — год",
        price_rub=5900,
        period="year",
        features=["Всё из Pro", "2 месяца в подарок", "Приоритетная поддержка"],
    ),
]
PAID_PLANS = {"pro_monthly", "pro_yearly"}
_ACTIVATE_EVENTS = {"subscription.activated", "payment.succeeded"}
_CANCEL_EVENTS = {"subscription.canceled", "subscription.expired"}


class BillingService:
    def __init__(self, db: AsyncSession, provider: PaymentProvider | None = None) -> None:
        self.db = db
        self.subs = SubscriptionRepository(db)
        self.users = UserRepository(db)
        self.provider = provider or get_payment_provider()

    def list_plans(self) -> list[PlanOut]:
        return PLANS

    async def subscribe(self, user: User, plan: str) -> SubscribeOut:
        if plan not in PAID_PLANS:
            raise ValidationAppError("Unknown plan", code="unknown_plan", details={"plan": plan})
        checkout = self.provider.create_checkout(
            user_id=user.id, plan=plan, return_url=f"{settings.web_base_url}/account"
        )
        sub = await self.subs.create(
            user_id=user.id,
            plan=plan,
            status="pending",
            provider=checkout.provider,
            provider_ref=checkout.provider_ref,
        )
        await self.db.commit()
        return SubscribeOut(
            checkout_url=checkout.checkout_url, subscription_id=sub.id, provider=checkout.provider
        )

    async def handle_webhook(self, headers: dict[str, str], raw_body: bytes) -> dict[str, str]:
        event = self.provider.parse_webhook(headers, raw_body)  # raises on bad signature
        sub = await self.subs.get_by_provider_ref(event.provider_ref)
        if sub is None:
            logger.warning("Webhook for unknown provider_ref=%s", event.provider_ref)
            return {"status": "ignored"}

        if event.type in _ACTIVATE_EVENTS:
            days = 365 if sub.plan == "pro_yearly" else 30
            await self.subs.activate(sub, datetime.now(timezone.utc) + timedelta(days=days))
            user = await self.users.get_by_id(sub.user_id)
            if user is not None:
                user.plan = "pro"
            await self.db.commit()
            return {"status": "activated"}

        if event.type in _CANCEL_EVENTS:
            await self.subs.cancel(sub)
            user = await self.users.get_by_id(sub.user_id)
            if user is not None:
                user.plan = "free"
            await self.db.commit()
            return {"status": "canceled"}

        return {"status": "ignored"}
