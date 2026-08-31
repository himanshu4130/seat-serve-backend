import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class QRStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class QRCode(Base):
    __tablename__ = "qr_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    service_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_points.id", ondelete="CASCADE"), unique=True, index=True
    )
    # The future `/v/{tenantSlug}/{servicePoint}` routing key (Phase 4 on the
    # frontend) — already the canonical public lookup key here so that route
    # can land without a backend change.
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[QRStatus] = mapped_column(Enum(QRStatus, native_enum=False), default=QRStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    service_point = relationship("ServicePoint", back_populates="qr_code")
