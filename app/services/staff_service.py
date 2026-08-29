import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.staff_business_role import StaffBusinessRole, StaffStatus
from app.repositories.staff_role_repository import StaffRoleRepository


class StaffService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.staff_roles = StaffRoleRepository(db)

    async def list_for_business(self, business_id: uuid.UUID) -> list[StaffBusinessRole]:
        return await self.staff_roles.list_for_business(business_id)

    async def invite(
        self, *, business_id: uuid.UUID, name: str, email: str, role: Role, phone: str | None
    ) -> StaffBusinessRole:
        existing = await self.staff_roles.get_by_email(business_id=business_id, email=email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="This email is already staff on this business"
            )
        return await self.staff_roles.add(
            business_id=business_id, role=role, name=name, email=email, phone=phone, status=StaffStatus.INVITED
        )

    async def _get_for_business(self, *, business_id: uuid.UUID, staff_role_id: uuid.UUID) -> StaffBusinessRole:
        staff_role = await self.staff_roles.get(staff_role_id)
        if staff_role is None or staff_role.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
        return staff_role

    async def update(
        self,
        *,
        business_id: uuid.UUID,
        staff_role_id: uuid.UUID,
        role: Role | None,
        status_: StaffStatus | None,
        phone: str | None,
    ) -> StaffBusinessRole:
        staff_role = await self._get_for_business(business_id=business_id, staff_role_id=staff_role_id)

        demoting_or_disabling_owner = staff_role.role == Role.OWNER and (
            (role is not None and role != Role.OWNER) or status_ == StaffStatus.DISABLED
        )
        if demoting_or_disabling_owner:
            all_staff = await self.staff_roles.list_for_business(business_id)
            other_active_owners = [
                s
                for s in all_staff
                if s.id != staff_role.id and s.role == Role.OWNER and s.status == StaffStatus.ACTIVE
            ]
            if not other_active_owners:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner of a business",
                )

        return await self.staff_roles.update(staff_role, role=role, status=status_, phone=phone)
