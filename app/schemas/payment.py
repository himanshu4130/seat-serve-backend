import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.payment import (
    PaymentConnectionStatus,
    PaymentMethod,
    PaymentProviderName,
    PaymentPurpose,
    PaymentStatus,
    RefundStatus,
)


class PaymentConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    provider: PaymentProviderName
    status: PaymentConnectionStatus
    account_ref: str | None


class PaymentTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    purpose: PaymentPurpose
    order_id: uuid.UUID | None
    invoice_id: uuid.UUID | None
    provider: PaymentProviderName
    amount: Decimal
    currency: str
    status: PaymentStatus
    method: PaymentMethod | None
    provider_order_id: str | None
    provider_payment_id: str | None
    failure_reason: str | None
    created_at: datetime


class CreateOrderPaymentResponse(BaseModel):
    transaction_id: uuid.UUID
    provider_order_id: str
    amount_minor: int
    currency: str
    key_id: str


class VerifyPaymentRequest(BaseModel):
    transaction_id: uuid.UUID
    provider_payment_id: str
    provider_signature: str


class RazorpayWebhookAck(BaseModel):
    status: str = "ok"


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    amount: Decimal
    status: RefundStatus
    provider_refund_id: str | None
    reason: str
    created_at: datetime
