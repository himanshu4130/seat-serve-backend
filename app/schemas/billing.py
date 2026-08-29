import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.billing import InvoiceStatus, PlanId
from app.models.business import SubscriptionState


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: PlanId
    name: str
    price: Decimal
    features: list[str]

    @classmethod
    def from_model(cls, plan) -> "PlanOut":
        return cls(
            id=plan.id,
            name=plan.name,
            price=plan.price,
            features=[line for line in plan.features.split("\n") if line],
        )


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    plan_id: PlanId
    state: SubscriptionState
    renewal_date: datetime | None


class SetPlanRequest(BaseModel):
    plan_id: PlanId


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    amount: Decimal
    status: InvoiceStatus
    issued_at: datetime
    paid_at: datetime | None
