import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class OrderStatus(StrEnum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    # Not modeled on the frontend yet (its ORDER_FLOW is linear, happy-path
    # only) but required for a real payments/refunds backend.
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


# The linear happy-path progression `advance()` steps through — matches the
# frontend's ORDER_FLOW exactly (src/lib/seatserve/data.ts).
ORDER_FLOW: list[OrderStatus] = [
    OrderStatus.NEW,
    OrderStatus.ACCEPTED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
]


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("business_id", "order_number", name="uq_business_order_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    service_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_points.id"), index=True)
    # Human-friendly per-business sequence, matching the frontend's numeric
    # order id (it starts seed data at 1048) without making UUIDs the customer
    # ever has to read out over a counter.
    order_number: Mapped[int] = mapped_column(Integer)
    # Snapshot of the service point at order time (zone/point display), so a
    # later service-point rename doesn't rewrite history.
    point_label: Mapped[str] = mapped_column(String(200), default="")
    zone_label: Mapped[str] = mapped_column(String(200), default="")
    customer_phone: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, native_enum=False), default=OrderStatus.NEW)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    special_instructions: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    service_point = relationship("ServicePoint")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    # Nullable + name/price snapshot: a later menu edit/delete must never
    # rewrite an already-placed order's history.
    menu_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("menu_items.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    image: Mapped[str] = mapped_column(String(500), default="")
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))

    order = relationship("Order", back_populates="items")
    addons = relationship("OrderItemAddon", back_populates="order_item", cascade="all, delete-orphan")


class OrderItemAddon(Base):
    __tablename__ = "order_item_addons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_items.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Numeric(10, 2))

    order_item = relationship("OrderItem", back_populates="addons")
