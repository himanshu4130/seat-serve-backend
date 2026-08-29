import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.staff_business_role import StaffBusinessRole, StaffStatus


class StaffRoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(
        self,
        *,
        business_id: uuid.UUID,
        role: Role,
        name: str,
        email: str,
        user_id: uuid.UUID | None = None,
        phone: str | None = None,
        status: StaffStatus = StaffStatus.ACTIVE,
    ) -> StaffBusinessRole:
        staff_role = StaffBusinessRole(
            user_id=user_id,
            business_id=business_id,
            role=role,
            name=name,
            email=email,
            phone=phone,
            status=status,
        )
        self.db.add(staff_role)
        await self.db.commit()
        await self.db.refresh(staff_role)
        return staff_role

    async def get_role(self, *, user_id: uuid.UUID, business_id: uuid.UUID) -> Role | None:
        result = await self.db.execute(
            select(StaffBusinessRole.role).where(
                StaffBusinessRole.user_id == user_id,
                StaffBusinessRole.business_id == business_id,
                StaffBusinessRole.status == StaffStatus.ACTIVE,
            )
        )
        role = result.scalar_one_or_none()
        return Role(role) if role else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[StaffBusinessRole]:
        result = await self.db.execute(select(StaffBusinessRole).where(StaffBusinessRole.user_id == user_id))
        return list(result.scalars().all())

    async def list_for_business(self, business_id: uuid.UUID) -> list[StaffBusinessRole]:
        result = await self.db.execute(
            select(StaffBusinessRole)
            .where(StaffBusinessRole.business_id == business_id)
            .order_by(StaffBusinessRole.created_at)
        )
        return list(result.scalars().all())

    async def get(self, staff_role_id: uuid.UUID) -> StaffBusinessRole | None:
        return await self.db.get(StaffBusinessRole, staff_role_id)

    async def get_by_email(self, *, business_id: uuid.UUID, email: str) -> StaffBusinessRole | None:
        result = await self.db.execute(
            select(StaffBusinessRole).where(
                StaffBusinessRole.business_id == business_id, StaffBusinessRole.email == email
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_invites_for_email(self, email: str) -> list[StaffBusinessRole]:
        result = await self.db.execute(
            select(StaffBusinessRole).where(
                StaffBusinessRole.email == email,
                StaffBusinessRole.status == StaffStatus.INVITED,
                StaffBusinessRole.user_id.is_(None),
            )
        )
        return list(result.scalars().all())

    async def link_user(self, staff_role: StaffBusinessRole, *, user_id: uuid.UUID) -> StaffBusinessRole:
        staff_role.user_id = user_id
        staff_role.status = StaffStatus.ACTIVE
        staff_role.last_active_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(staff_role)
        return staff_role

    async def update(
        self,
        staff_role: StaffBusinessRole,
        *,
        role: Role | None = None,
        status: StaffStatus | None = None,
        phone: str | None = None,
    ) -> StaffBusinessRole:
        if role is not None:
            staff_role.role = role
        if status is not None:
            staff_role.status = status
        if phone is not None:
            staff_role.phone = phone
        await self.db.commit()
        await self.db.refresh(staff_role)
        return staff_role

    async def touch_last_active(self, staff_role: StaffBusinessRole) -> None:
        staff_role.last_active_at = datetime.now(timezone.utc)
        await self.db.commit()
