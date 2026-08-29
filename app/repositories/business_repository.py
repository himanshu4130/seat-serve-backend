import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business, BusinessType
from app.models.staff_business_role import StaffBusinessRole


class BusinessRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, tenant_id: uuid.UUID, name: str, emoji: str, business_type: BusinessType, city: str
    ) -> Business:
        business = Business(
            tenant_id=tenant_id, name=name, emoji=emoji, business_type=business_type, city=city
        )
        self.db.add(business)
        await self.db.commit()
        await self.db.refresh(business)
        return business

    async def get(self, business_id: uuid.UUID) -> Business | None:
        return await self.db.get(Business, business_id)

    async def list_all(self) -> list[Business]:
        result = await self.db.execute(select(Business))
        return list(result.scalars().all())

    async def list_for_user(self, user_id: uuid.UUID) -> list[Business]:
        result = await self.db.execute(
            select(Business)
            .join(StaffBusinessRole, StaffBusinessRole.business_id == Business.id)
            .where(StaffBusinessRole.user_id == user_id)
        )
        return list(result.scalars().all())
