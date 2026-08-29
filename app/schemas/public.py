import uuid

from pydantic import BaseModel, ConfigDict

from app.models.business import BusinessType
from app.schemas.service_point import ServicePointOut


class PublicBusinessOut(BaseModel):
    """What an unauthenticated customer scanning a QR code is allowed to see
    about the business — never tenant_id/subscription_state/tax rate."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    emoji: str
    business_type: BusinessType
    city: str


class QRResolveOut(BaseModel):
    business: PublicBusinessOut
    service_point: ServicePointOut
