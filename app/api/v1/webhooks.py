from fastapi import APIRouter, Depends, Header, Request

from app.api.v1.deps import get_payment_provider, get_payment_service
from app.schemas.payment import RazorpayWebhookAck
from app.services.payment_service import PaymentService
from app.services.payments.base import PaymentProvider

router = APIRouter()


@router.post("/razorpay", response_model=RazorpayWebhookAck)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    service: PaymentService = Depends(get_payment_service),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> RazorpayWebhookAck:
    raw_body = await request.body()
    await service.handle_webhook(raw_body=raw_body, signature=x_razorpay_signature, provider=provider)
    return RazorpayWebhookAck()
