import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderItemAddon, OrderStatus


class OrderItemInput:
    __slots__ = ("menu_item_id", "name", "unit_price", "quantity", "image", "addons")

    def __init__(
        self,
        *,
        menu_item_id: uuid.UUID | None,
        name: str,
        unit_price: float,
        quantity: int,
        image: str,
        addons: list[tuple[str, float]],
    ):
        self.menu_item_id = menu_item_id
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity
        self.image = image
        self.addons = addons


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _next_order_number(self, business_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.max(Order.order_number)).where(Order.business_id == business_id)
        )
        current_max = result.scalar_one_or_none()
        return (current_max or 1000) + 1

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        service_point_id: uuid.UUID,
        point_label: str,
        zone_label: str,
        customer_phone: str,
        items: list[OrderItemInput],
        subtotal: float,
        tax_amount: float,
        total: float,
        special_instructions: str = "",
    ) -> Order:
        order = Order(
            business_id=business_id,
            service_point_id=service_point_id,
            order_number=await self._next_order_number(business_id),
            point_label=point_label,
            zone_label=zone_label,
            customer_phone=customer_phone,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            special_instructions=special_instructions,
        )
        for item_input in items:
            line_total = item_input.unit_price * item_input.quantity + sum(
                price * item_input.quantity for _, price in item_input.addons
            )
            order_item = OrderItem(
                menu_item_id=item_input.menu_item_id,
                name=item_input.name,
                unit_price=item_input.unit_price,
                quantity=item_input.quantity,
                image=item_input.image,
                line_total=line_total,
            )
            order_item.addons = [
                OrderItemAddon(name=addon_name, price=addon_price)
                for addon_name, addon_price in item_input.addons
            ]
            order.items.append(order_item)

        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order, attribute_names=["items"])
        return order

    async def get(self, order_id: uuid.UUID) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.addons))
        )
        return result.scalar_one_or_none()

    async def list_for_business(
        self,
        business_id: uuid.UUID,
        *,
        status: OrderStatus | None = None,
        created_after=None,
        created_before=None,
    ) -> list[Order]:
        query = (
            select(Order)
            .where(Order.business_id == business_id)
            .options(selectinload(Order.items).selectinload(OrderItem.addons))
            .order_by(Order.created_at.desc())
        )
        if status is not None:
            query = query.where(Order.status == status)
        if created_after is not None:
            query = query.where(Order.created_at >= created_after)
        if created_before is not None:
            query = query.where(Order.created_at < created_before)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_for_phone(self, *, business_id: uuid.UUID | None, phone: str) -> list[Order]:
        query = (
            select(Order)
            .where(Order.customer_phone == phone)
            .options(selectinload(Order.items).selectinload(OrderItem.addons))
            .order_by(Order.created_at.desc())
        )
        if business_id is not None:
            query = query.where(Order.business_id == business_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def set_status(self, order: Order, *, status: OrderStatus) -> Order:
        order.status = status
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def set_paid(self, order: Order, *, paid: bool) -> Order:
        order.paid = paid
        await self.db.commit()
        await self.db.refresh(order)
        return order
