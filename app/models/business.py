import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class BusinessType(StrEnum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    THEATRE = "theatre"
    CINEMA = "cinema"
    HOTEL = "hotel"
    RESORT = "resort"
    STADIUM = "stadium"
    FOOD_COURT = "food_court"
    EVENT = "event"
    LOUNGE = "lounge"
    OTHER = "other"


class SubscriptionState(StrEnum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    emoji: Mapped[str] = mapped_column(String(16), default="🏢")
    business_type: Mapped[BusinessType] = mapped_column(Enum(BusinessType, native_enum=False))
    city: Mapped[str] = mapped_column(String(200), default="")
    subscription_state: Mapped[SubscriptionState] = mapped_column(
        Enum(SubscriptionState, native_enum=False), default=SubscriptionState.TRIAL
    )
    # Basis points (1800 = 18.00%), matching the frontend's currently-hardcoded
    # 18% GST receipt line — now computed server-side per order instead.
    tax_rate_bp: Mapped[int] = mapped_column(Integer, default=1800)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tenant = relationship("Tenant", back_populates="businesses")
    staff_roles = relationship("StaffBusinessRole", back_populates="business")
