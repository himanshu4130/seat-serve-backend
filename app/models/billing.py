import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.business import SubscriptionState


class PlanId(StrEnum):
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    SCALE = "SCALE"


class InvoiceStatus(StrEnum):
    PAID = "PAID"
    PENDING = "PENDING"
    FAILED = "FAILED"


class Plan(Base):
    """Seeded catalog (see the initial migration's data), not user-editable
    through the API in this phase."""

    __tablename__ = "plans"

    id: Mapped[PlanId] = mapped_column(Enum(PlanId, native_enum=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    features: Mapped[str] = mapped_column(String(2000), default="")  # newline-joined bullet list


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), unique=True, index=True)
    plan_id: Mapped[PlanId] = mapped_column(ForeignKey("plans.id"))
    state: Mapped[SubscriptionState] = mapped_column(
        Enum(SubscriptionState, native_enum=False), default=SubscriptionState.TRIAL
    )
    renewal_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    plan = relationship("Plan")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus, native_enum=False), default=InvoiceStatus.PENDING)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription = relationship("Subscription", back_populates="invoices")
