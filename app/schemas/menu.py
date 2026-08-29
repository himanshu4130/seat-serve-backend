import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MenuCategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class MenuCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    sort_order: int


class AddonIn(BaseModel):
    name: str
    price: Decimal = Field(ge=0)


class AddonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    price: Decimal


class MenuItemCreate(BaseModel):
    category_id: uuid.UUID
    name: str
    price: Decimal = Field(ge=0)
    image: str = ""
    description: str = ""
    addons: list[AddonIn] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    image: str | None = None
    description: str | None = None
    available: bool | None = None


class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    price: Decimal
    image: str
    description: str
    available: bool
    addons: list[AddonOut]
