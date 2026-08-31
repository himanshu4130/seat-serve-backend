import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.venue import VenueType


class VenueCreate(BaseModel):
    name: str
    venue_type: VenueType = VenueType.SCREEN
    capacity: int = 0
    description: Optional[str] = None


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    venue_type: Optional[VenueType] = None
    capacity: Optional[int] = None
    description: Optional[str] = None


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    venue_type: VenueType
    capacity: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
