"""Payment provider abstraction.

The MVP ships a :class:`StubPaymentProvider` so the full subscribe → webhook → activate
flow works end-to-end offline. A real ЮKassa/CloudPayments adapter implements the same
two methods and is selected in :func:`get_payment_provider` — no service-layer changes.
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.errors import AppError


@dataclass
class CheckoutSession:
    checkout_url: str
    provider_ref: str
    provider: str


@dataclass
class BillingEvent:
    type: str
    provider_ref: str
    plan: str | None = None


class BillingSignatureError(AppError):
    status_code = 400
    code = "invalid_signature"


class PaymentProvider(abc.ABC):
    name: str

    @abc.abstractmethod
    def create_checkout(self, *, user_id: uuid.UUID, plan: str, return_url: str) -> CheckoutSession:
        ...

    @abc.abstractmethod
    def parse_webhook(self, headers: dict[str, str], raw_body: bytes) -> BillingEvent:
        ...


class StubPaymentProvider(PaymentProvider):
    """Dev/offline provider: checkout URL points at a confirm page; webhooks are HMAC-signed
    with ``billing_webhook_secret`` so the activation path is exercised exactly like a real one."""

    name = "stub"

    def create_checkout(self, *, user_id: uuid.UUID, plan: str, return_url: str) -> CheckoutSession:
        ref = f"stub_{uuid.uuid4().hex}"
        url = (
            f"{settings.public_base_url}/billing/stub/checkout"
            f"?ref={ref}&plan={plan}&return_url={return_url}"
        )
        return CheckoutSession(checkout_url=url, provider_ref=ref, provider=self.name)

    @staticmethod
    def sign(raw_body: bytes) -> str:
        return hmac.new(
            settings.billing_webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()

    def parse_webhook(self, headers: dict[str, str], raw_body: bytes) -> BillingEvent:
        provided = headers.get("x-stub-signature", "")
        if not hmac.compare_digest(provided, self.sign(raw_body)):
            raise BillingSignatureError("Invalid webhook signature")
        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise BillingSignatureError("Invalid webhook body") from exc
        return BillingEvent(
            type=str(data.get("type", "")),
            provider_ref=str(data.get("provider_ref", "")),
            plan=data.get("plan"),
        )


def get_payment_provider() -> PaymentProvider:
    # Only the stub is implemented for the MVP; vendor adapters slot in here by name.
    return StubPaymentProvider()
