import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class VenueType(StrEnum):
    SCREEN = "SCREEN"
    FLOOR = "FLOOR"
    DECK = "DECK"
    ZONE = "ZONE"
    ROOM = "ROOM"
    CABANA = "CABANA"
    COUNTER = "COUNTER"
    CUSTOM = "CUSTOM"


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    venue_type: Mapped[VenueType] = mapped_column(String(50), default=VenueType.SCREEN)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    business = relationship("Business", back_populates="venues")
