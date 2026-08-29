import uuid

from pydantic import BaseModel, ConfigDict

from app.models.service_point import ServicePointKind


class ServiceAreaCreate(BaseModel):
    name: str


class ServiceAreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str


class ServicePointCreate(BaseModel):
    area_id: uuid.UUID
    code: str
    kind: ServicePointKind
    label: str = ""


class ServicePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    area_id: uuid.UUID
    code: str
    kind: ServicePointKind
    label: str
    active: bool


class ServicePointStatusUpdate(BaseModel):
    active: bool
