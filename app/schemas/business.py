import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.business import BusinessType, SubscriptionState


class BusinessCreate(BaseModel):
    name: str
    business_type: BusinessType
    city: str = ""
    emoji: str = "🏢"
    description: Optional[str] = None
    phone: Optional[str] = None
    currency: str = "INR"
    address_line1: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    business_type: Optional[BusinessType] = None
    city: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    currency: Optional[str] = None
    address_line1: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    emoji: str
    business_type: BusinessType
    city: str
    description: Optional[str] = None
    phone: Optional[str] = None
    currency: str
    address_line1: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    subscription_state: SubscriptionState
    created_at: datetime
    updated_at: datetime
