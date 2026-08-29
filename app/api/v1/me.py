from fastapi import APIRouter, Depends

from app.api.v1.deps import get_business_service
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.me import MeOut, MyBusiness
from app.schemas.user import UserOut
from app.services.business_service import BusinessService

router = APIRouter()


@router.get("/me", response_model=MeOut)
async def read_me(
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> MeOut:
    businesses = await service.list_my_businesses(current_user)
    my_businesses = []
    for business in businesses:
        role = await service.get_role_for_user(current_user=current_user, business_id=business.id)
        my_businesses.append(MyBusiness(business=business, role=role))
    return MeOut(user=UserOut.model_validate(current_user), businesses=my_businesses)
