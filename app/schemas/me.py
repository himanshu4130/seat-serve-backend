from pydantic import BaseModel

from app.core.permissions import Role
from app.schemas.business import BusinessOut
from app.schemas.user import UserOut


class MyBusiness(BaseModel):
    business: BusinessOut
    role: Role


class MeOut(BaseModel):
    user: UserOut
    businesses: list[MyBusiness]
