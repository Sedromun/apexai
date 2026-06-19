from fastapi import APIRouter, Request

from app.core.deps import BillingServiceDep, CurrentUser
from app.schemas.billing import PlanOut, SubscribeOut, SubscribeRequest, WebhookAck

router = APIRouter(tags=["billing"])


@router.get("/billing/plans", response_model=list[PlanOut])
async def plans(service: BillingServiceDep) -> list[PlanOut]:
    return service.list_plans()


@router.post("/billing/subscribe", response_model=SubscribeOut)
async def subscribe(
    body: SubscribeRequest, user: CurrentUser, service: BillingServiceDep
) -> SubscribeOut:
    """Create a pending subscription and return the provider checkout URL."""
    return await service.subscribe(user, body.plan)


@router.post("/billing/webhook", response_model=WebhookAck)
async def webhook(request: Request, service: BillingServiceDep) -> WebhookAck:
    """Provider → server callback. Signature-verified; activates/cancels the subscription."""
    raw_body = await request.body()
    result = await service.handle_webhook(dict(request.headers), raw_body)
    return WebhookAck(**result)
