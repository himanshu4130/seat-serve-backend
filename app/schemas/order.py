import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1)
    addon_names: list[str] = Field(default_factory=list)


class OrderCreate(BaseModel):
    service_point_id: uuid.UUID
    customer_phone: str = Field(min_length=6, max_length=32)
    items: list[OrderItemCreate] = Field(min_length=1)
    special_instructions: str = ""


class OrderItemAddonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    price: Decimal


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    unit_price: Decimal
    quantity: int
    image: str
    line_total: Decimal
    addons: list[OrderItemAddonOut]


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    service_point_id: uuid.UUID
    order_number: int
    point_label: str
    zone_label: str
    customer_phone: str
    status: OrderStatus
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    paid: bool
    special_instructions: str
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderRefundRequest(BaseModel):
    reason: str = ""
