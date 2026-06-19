from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AccountLimits(BaseModel):
    free_monthly_lap_limit: int
    free_ai_trial: int


class AccountUsage(BaseModel):
    laps_this_month: int
    ai_reports_used: int


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan: str
    status: str
    current_period_end: datetime | None


class AccountOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    lang: str
    plan: str
    limits: AccountLimits
    usage: AccountUsage
    subscription: SubscriptionOut | None = None
