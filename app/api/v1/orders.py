import uuid

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_order_service, get_payment_provider, get_payment_service, require_business_permission
from app.core.permissions import Permission
from app.models.order import OrderStatus
from app.schemas.order import OrderOut, OrderRefundRequest, OrderStatusUpdate
from app.schemas.payment import RefundOut
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.payments.base import PaymentProvider

router = APIRouter()


@router.get("", response_model=list[OrderOut])
async def list_orders(
    business_id: uuid.UUID,
    status_filter: OrderStatus | None = None,
    _=Depends(require_business_permission(Permission.ORDERS_VIEW)),
    service: OrderService = Depends(get_order_service),
) -> list[OrderOut]:
    orders = await service.list_for_business(business_id, status_filter=status_filter)
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.ORDERS_VIEW)),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.get_for_business(business_id=business_id, order_id=order_id)
    return OrderOut.model_validate(order)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def set_order_status(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    _=Depends(require_business_permission(Permission.ORDERS_MANAGE)),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.set_status(business_id=business_id, order_id=order_id, new_status=payload.status)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/advance", response_model=OrderOut)
async def advance_order(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.ORDERS_MANAGE)),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.advance(business_id=business_id, order_id=order_id)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/refund", response_model=RefundOut)
async def refund_order(
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    payload: OrderRefundRequest,
    _=Depends(require_business_permission(Permission.PAYMENTS_REFUND)),
    service: PaymentService = Depends(get_payment_service),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> RefundOut:
    refund = await service.create_refund(
        business_id=business_id, order_id=order_id, reason=payload.reason, provider=provider
    )
    return RefundOut.model_validate(refund)
