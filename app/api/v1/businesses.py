import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_business_service
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessOut
from app.services.business_service import BusinessService

router = APIRouter()


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> BusinessOut:
    business = await service.create_business(
        current_user=current_user,
        name=payload.name,
        emoji=payload.emoji,
        business_type=payload.business_type,
        city=payload.city,
    )
    return BusinessOut.model_validate(business)


@router.get("", response_model=list[BusinessOut])
async def list_businesses(
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> list[BusinessOut]:
    businesses = await service.list_my_businesses(current_user)
    return [BusinessOut.model_validate(b) for b in businesses]


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> BusinessOut:
    business = await service.get_business_for_user(current_user=current_user, business_id=business_id)
    return BusinessOut.model_validate(business)
