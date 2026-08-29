import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, name: str, owner_user_id: uuid.UUID) -> Tenant:
        tenant = Tenant(name=name, owner_user_id=owner_user_id)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def list_all(self) -> list[Tenant]:
        result = await self.db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        return list(result.scalars().all())
