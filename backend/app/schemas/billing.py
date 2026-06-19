from __future__ import annotations

import uuid

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: str
    title: str
    price_rub: int
    period: str | None
    features: list[str]


class SubscribeRequest(BaseModel):
    plan: str


class SubscribeOut(BaseModel):
    checkout_url: str
    subscription_id: uuid.UUID
    provider: str


class WebhookAck(BaseModel):
    status: str
