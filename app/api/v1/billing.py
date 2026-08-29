import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_billing_service, get_payment_provider, require_business_permission
from app.core.permissions import Permission
from app.schemas.billing import InvoiceOut, PlanOut, SetPlanRequest, SubscriptionOut
from app.schemas.payment import CreateOrderPaymentResponse
from app.services.billing_service import BillingService
from app.services.payments.base import PaymentProvider

# Mounted at /api/v1/billing — plan catalog isn't scoped to a business.
plans_router = APIRouter()


@plans_router.get("/plans", response_model=list[PlanOut])
async def list_plans(service: BillingService = Depends(get_billing_service)) -> list[PlanOut]:
    plans = await service.list_plans()
    return [PlanOut.from_model(p) for p in plans]


# Mounted at /api/v1/businesses/{business_id}/billing
router = APIRouter()


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.BILLING_MANAGE)),
    service: BillingService = Depends(get_billing_service),
) -> SubscriptionOut:
    subscription = await service.get_subscription(business_id)
    return SubscriptionOut.model_validate(subscription)


@router.post("/subscription", response_model=SubscriptionOut)
async def set_plan(
    business_id: uuid.UUID,
    payload: SetPlanRequest,
    _=Depends(require_business_permission(Permission.BILLING_MANAGE)),
    service: BillingService = Depends(get_billing_service),
) -> SubscriptionOut:
    subscription = await service.set_plan(business_id=business_id, plan_id=payload.plan_id)
    return SubscriptionOut.model_validate(subscription)


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.BILLING_MANAGE)),
    service: BillingService = Depends(get_billing_service),
) -> list[InvoiceOut]:
    invoices = await service.list_invoices(business_id)
    return [InvoiceOut.model_validate(i) for i in invoices]


@router.post("/invoices/{invoice_id}/pay", response_model=CreateOrderPaymentResponse)
async def pay_invoice(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.BILLING_MANAGE)),
    service: BillingService = Depends(get_billing_service),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> CreateOrderPaymentResponse:
    transaction, provider_order = await service.create_invoice_payment(
        business_id=business_id, invoice_id=invoice_id, provider=provider
    )
    return CreateOrderPaymentResponse(
        transaction_id=transaction.id,
        provider_order_id=provider_order.provider_order_id,
        amount_minor=provider_order.amount_minor,
        currency=provider_order.currency,
        key_id=provider_order.key_id,
    )
