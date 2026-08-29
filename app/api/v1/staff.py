import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_staff_service, require_business_permission
from app.core.permissions import Permission
from app.schemas.staff import StaffInviteCreate, StaffOut, StaffUpdate
from app.services.staff_service import StaffService

router = APIRouter()


@router.get("", response_model=list[StaffOut])
async def list_staff(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.STAFF_MANAGE)),
    service: StaffService = Depends(get_staff_service),
) -> list[StaffOut]:
    staff = await service.list_for_business(business_id)
    return [StaffOut.model_validate(s) for s in staff]


@router.post("", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    business_id: uuid.UUID,
    payload: StaffInviteCreate,
    _=Depends(require_business_permission(Permission.STAFF_MANAGE)),
    service: StaffService = Depends(get_staff_service),
) -> StaffOut:
    staff = await service.invite(
        business_id=business_id, name=payload.name, email=payload.email, role=payload.role, phone=payload.phone
    )
    return StaffOut.model_validate(staff)


@router.patch("/{staff_id}", response_model=StaffOut)
async def update_staff(
    business_id: uuid.UUID,
    staff_id: uuid.UUID,
    payload: StaffUpdate,
    _=Depends(require_business_permission(Permission.STAFF_MANAGE)),
    service: StaffService = Depends(get_staff_service),
) -> StaffOut:
    staff = await service.update(
        business_id=business_id, staff_role_id=staff_id, role=payload.role, status_=payload.status, phone=payload.phone
    )
    return StaffOut.model_validate(staff)
