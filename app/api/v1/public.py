import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import (
    get_business_service,
    get_menu_service,
    get_order_service,
    get_payment_provider,
    get_payment_service,
    get_qr_service,
    get_service_point_service,
)
from app.schemas.menu import MenuCategoryOut, MenuItemOut
from app.schemas.order import OrderCreate, OrderOut
from app.schemas.payment import CreateOrderPaymentResponse, VerifyPaymentRequest, PaymentTransactionOut
from app.schemas.public import PublicBusinessOut, QRResolveOut
from app.services.business_service import BusinessService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.payments.base import PaymentProvider
from app.services.qr_service import QRService
from app.services.service_point_service import ServicePointService

router = APIRouter()


@router.get("/qr/{slug}", response_model=QRResolveOut)
async def resolve_qr_slug(
    slug: str,
    qr_service: QRService = Depends(get_qr_service),
    point_service: ServicePointService = Depends(get_service_point_service),
    business_service: BusinessService = Depends(get_business_service),
) -> QRResolveOut:
    qr_code = await qr_service.get_by_slug(slug)
    service_point = await point_service.get_point_for_business(
        business_id=qr_code.business_id, point_id=qr_code.service_point_id
    )
    business = await business_service.businesses.get(qr_code.business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return QRResolveOut(
        business=PublicBusinessOut.model_validate(business), service_point=service_point
    )


@router.get("/businesses/{business_id}/menu/categories", response_model=list[MenuCategoryOut])
async def public_list_categories(
    business_id: uuid.UUID, service: MenuService = Depends(get_menu_service)
) -> list[MenuCategoryOut]:
    return [MenuCategoryOut.model_validate(c) for c in await service.list_categories(business_id)]


@router.get("/businesses/{business_id}/menu/items", response_model=list[MenuItemOut])
async def public_list_items(
    business_id: uuid.UUID, service: MenuService = Depends(get_menu_service)
) -> list[MenuItemOut]:
    return [MenuItemOut.model_validate(i) for i in await service.list_items(business_id)]


@router.post(
    "/businesses/{business_id}/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED
)
async def create_order(
    business_id: uuid.UUID, payload: OrderCreate, service: OrderService = Depends(get_order_service)
) -> OrderOut:
    order = await service.create_order(
        business_id=business_id,
        service_point_id=payload.service_point_id,
        customer_phone=payload.customer_phone,
        items=payload.items,
        special_instructions=payload.special_instructions,
    )
    return OrderOut.model_validate(order)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    phone: str = Query(..., description="Customer phone used to place the order"),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.get_for_customer(order_id=order_id, phone=phone)
    return OrderOut.model_validate(order)


@router.get("/orders", response_model=list[OrderOut])
async def list_my_orders(
    phone: str = Query(...),
    business_id: uuid.UUID | None = None,
    service: OrderService = Depends(get_order_service),
) -> list[OrderOut]:
    orders = await service.list_for_customer(business_id=business_id, phone=phone)
    return [OrderOut.model_validate(o) for o in orders]


@router.post("/orders/{order_id}/payment", response_model=CreateOrderPaymentResponse)
async def create_order_payment(
    order_id: uuid.UUID,
    phone: str = Query(...),
    order_service: OrderService = Depends(get_order_service),
    payment_service: PaymentService = Depends(get_payment_service),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> CreateOrderPaymentResponse:
    order = await order_service.get_for_customer(order_id=order_id, phone=phone)
    transaction, provider_order = await payment_service.create_order_payment(
        business_id=order.business_id, order_id=order.id, provider=provider
    )
    return CreateOrderPaymentResponse(
        transaction_id=transaction.id,
        provider_order_id=provider_order.provider_order_id,
        amount_minor=provider_order.amount_minor,
        currency=provider_order.currency,
        key_id=provider_order.key_id,
    )


@router.post("/payments/verify", response_model=PaymentTransactionOut)
async def verify_payment(
    payload: VerifyPaymentRequest,
    service: PaymentService = Depends(get_payment_service),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> PaymentTransactionOut:
    transaction = await service.verify_payment(
        transaction_id=payload.transaction_id,
        provider_payment_id=payload.provider_payment_id,
        provider_signature=payload.provider_signature,
        provider=provider,
    )
    return PaymentTransactionOut.model_validate(transaction)
