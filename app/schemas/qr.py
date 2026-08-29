import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.qr import QRStatus


class QRCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    service_point_id: uuid.UUID
    slug: str
    status: QRStatus
    created_at: datetime


class QRCodeCreate(BaseModel):
    service_point_id: uuid.UUID
