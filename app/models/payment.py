import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PaymentProviderName(StrEnum):
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PHONEPE = "phonepe"


class PaymentConnectionStatus(StrEnum):
    CONNECTED = "CONNECTED"
    NOT_CONNECTED = "NOT_CONNECTED"
    ACTION_REQUIRED = "ACTION_REQUIRED"


class PaymentStatus(StrEnum):
    IDLE = "IDLE"
    CREATING = "CREATING"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    REFUNDED = "REFUNDED"


class PaymentMethod(StrEnum):
    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"


class PaymentPurpose(StrEnum):
    ORDER = "ORDER"
    SUBSCRIPTION_INVOICE = "SUBSCRIPTION_INVOICE"


class RefundStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class PaymentConfig(Base):
    """Per-business payment settings. Never holds a secret key — only a
    public-safe reference to how this business is connected. The actual
    provider credential lives in Settings (platform-level) or, for a future
    Razorpay Route/sub-merchant model, in a secrets store — never here."""

    __tablename__ = "payment_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), unique=True, index=True)
    provider: Mapped[PaymentProviderName] = mapped_column(
        Enum(PaymentProviderName, native_enum=False), default=PaymentProviderName.RAZORPAY
    )
    status: Mapped[PaymentConnectionStatus] = mapped_column(
        Enum(PaymentConnectionStatus, native_enum=False), default=PaymentConnectionStatus.NOT_CONNECTED
    )
    account_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(Enum(PaymentPurpose, native_enum=False))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    provider: Mapped[PaymentProviderName] = mapped_column(Enum(PaymentProviderName, native_enum=False))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, native_enum=False), default=PaymentStatus.IDLE)
    method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod, native_enum=False), nullable=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    refunds = relationship("Refund", back_populates="transaction")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_transactions.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[RefundStatus] = mapped_column(Enum(RefundStatus, native_enum=False), default=RefundStatus.PENDING)
    provider_refund_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    transaction = relationship("PaymentTransaction", back_populates="refunds")


class PaymentWebhookEvent(Base):
    """Append-only log of every inbound webhook call, kept for idempotency
    (provider_event_id is unique — a redelivered webhook is a no-op) and for
    audit/debugging of what the provider actually sent."""

    __tablename__ = "payment_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_provider_event"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[PaymentProviderName] = mapped_column(Enum(PaymentProviderName, native_enum=False))
    provider_event_id: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    signature_valid: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
