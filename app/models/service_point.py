import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ServicePointKind(StrEnum):
    SEAT = "SEAT"
    TABLE = "TABLE"
    ROOM = "ROOM"
    CABANA = "CABANA"
    CHAIR = "CHAIR"
    COUNTER = "COUNTER"
    CUSTOM = "CUSTOM"


class ServiceArea(Base):
    __tablename__ = "service_areas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    points = relationship("ServicePoint", back_populates="area")


class ServicePoint(Base):
    __tablename__ = "service_points"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    area_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_areas.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    kind: Mapped[ServicePointKind] = mapped_column(Enum(ServicePointKind, native_enum=False))
    label: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    area = relationship("ServiceArea", back_populates="points")
    qr_code = relationship("QRCode", back_populates="service_point", uselist=False)
