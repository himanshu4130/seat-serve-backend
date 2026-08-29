import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.permissions import Role
from app.models.staff_business_role import StaffStatus


class StaffInviteCreate(BaseModel):
    name: str
    # Plain str, not EmailStr, to avoid pulling in the optional
    # `email-validator` dependency for one field; format is loose by design.
    email: str = Field(min_length=3, max_length=320)
    role: Role
    phone: str | None = None


class StaffUpdate(BaseModel):
    role: Role | None = None
    status: StaffStatus | None = None
    phone: str | None = None


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    email: str
    phone: str | None
    role: Role
    status: StaffStatus
    last_active_at: datetime | None
