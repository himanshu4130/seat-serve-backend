import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.business import BusinessType, SubscriptionState


class BusinessCreate(BaseModel):
    name: str
    business_type: BusinessType
    city: str = ""
    emoji: str = "🏢"


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    emoji: str
    business_type: BusinessType
    city: str
    subscription_state: SubscriptionState
    created_at: datetime
