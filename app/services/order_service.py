import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ORDER_FLOW, Order, OrderStatus
from app.repositories.business_repository import BusinessRepository
from app.repositories.menu_repository import MenuItemRepository
from app.repositories.order_repository import OrderItemInput, OrderRepository
from app.repositories.service_point_repository import ServicePointRepository
from app.schemas.order import OrderItemCreate

# Terminal/branch transitions a staff member (or the system, for CANCELLED)
# may make. Anything not listed here is rejected — no skipping straight from
# NEW to DELIVERED, no reviving a CANCELLED/REFUNDED order.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NEW: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: {OrderStatus.REFUNDED},
    OrderStatus.REFUNDED: set(),
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.orders = OrderRepository(db)
        self.menu_items = MenuItemRepository(db)
        self.service_points = ServicePointRepository(db)
        self.businesses = BusinessRepository(db)

    async def create_order(
        self,
        *,
        business_id: uuid.UUID,
        service_point_id: uuid.UUID,
        customer_phone: str,
        items: list[OrderItemCreate],
        special_instructions: str,
    ) -> Order:
        business = await self.businesses.get(business_id)
        if business is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

        point = await self.service_points.get(service_point_id)
        if point is None or point.business_id != business_id or not point.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service point not found or inactive")

        # Prices are ALWAYS recomputed from the current menu row — the
        # client only ever sends item ids, quantities, and addon names.
        item_inputs: list[OrderItemInput] = []
        subtotal = Decimal("0")
        for requested in items:
            menu_item = await self.menu_items.get(requested.menu_item_id)
            if menu_item is None or menu_item.business_id != business_id or not menu_item.available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Menu item {requested.menu_item_id} is not available",
                )
            available_addons = {addon.name: Decimal(str(addon.price)) for addon in menu_item.addons}
            resolved_addons: list[tuple[str, Decimal]] = []
            for addon_name in requested.addon_names:
                if addon_name not in available_addons:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown addon '{addon_name}' for item {menu_item.name}",
                    )
                resolved_addons.append((addon_name, available_addons[addon_name]))

            unit_price = Decimal(str(menu_item.price))
            line_total = (unit_price + sum((p for _, p in resolved_addons), Decimal("0"))) * requested.quantity
            subtotal += line_total
            item_inputs.append(
                OrderItemInput(
                    menu_item_id=menu_item.id,
                    name=menu_item.name,
                    unit_price=unit_price,
                    quantity=requested.quantity,
                    image=menu_item.image,
                    addons=resolved_addons,
                )
            )

        tax_amount = (subtotal * Decimal(business.tax_rate_bp) / Decimal(10000)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total = subtotal + tax_amount

        return await self.orders.create(
            business_id=business_id,
            service_point_id=service_point_id,
            point_label=point.label or point.code,
            zone_label=point.area.name if point.area else "",
            customer_phone=customer_phone,
            items=item_inputs,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            special_instructions=special_instructions,
        )

    async def list_for_business(self, business_id: uuid.UUID, *, status_filter: OrderStatus | None = None) -> list[Order]:
        return await self.orders.list_for_business(business_id, status=status_filter)

    async def get_for_business(self, *, business_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        order = await self.orders.get(order_id)
        if order is None or order.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def get_for_customer(self, *, order_id: uuid.UUID, phone: str) -> Order:
        order = await self.orders.get(order_id)
        if order is None or order.customer_phone != phone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def list_for_customer(self, *, business_id: uuid.UUID | None, phone: str) -> list[Order]:
        return await self.orders.list_for_phone(business_id=business_id, phone=phone)

    def _apply_transition(self, order: Order, new_status: OrderStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot move order from {order.status} to {new_status}",
            )

    async def set_status(self, *, business_id: uuid.UUID, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
        order = await self.get_for_business(business_id=business_id, order_id=order_id)
        self._apply_transition(order, new_status)
        return await self.orders.set_status(order, status=new_status)

    async def advance(self, *, business_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        order = await self.get_for_business(business_id=business_id, order_id=order_id)
        try:
            next_status = ORDER_FLOW[ORDER_FLOW.index(order.status) + 1]
        except (ValueError, IndexError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Order has no further status to advance to"
            ) from exc
        self._apply_transition(order, next_status)
        return await self.orders.set_status(order, status=next_status)
