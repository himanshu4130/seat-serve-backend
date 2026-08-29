import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.service_point import ServiceArea, ServicePoint, ServicePointKind


class ServiceAreaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, business_id: uuid.UUID, name: str) -> ServiceArea:
        area = ServiceArea(business_id=business_id, name=name)
        self.db.add(area)
        await self.db.commit()
        await self.db.refresh(area)
        return area

    async def get(self, area_id: uuid.UUID) -> ServiceArea | None:
        return await self.db.get(ServiceArea, area_id)

    async def list_for_business(self, business_id: uuid.UUID) -> list[ServiceArea]:
        result = await self.db.execute(
            select(ServiceArea).where(ServiceArea.business_id == business_id).order_by(ServiceArea.name)
        )
        return list(result.scalars().all())


class ServicePointRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        area_id: uuid.UUID,
        code: str,
        kind: ServicePointKind,
        label: str,
    ) -> ServicePoint:
        point = ServicePoint(business_id=business_id, area_id=area_id, code=code, kind=kind, label=label)
        self.db.add(point)
        await self.db.commit()
        await self.db.refresh(point)
        return point

    async def get(self, point_id: uuid.UUID) -> ServicePoint | None:
        result = await self.db.execute(
            select(ServicePoint).where(ServicePoint.id == point_id).options(selectinload(ServicePoint.area))
        )
        return result.scalar_one_or_none()

    async def list_for_business(self, business_id: uuid.UUID) -> list[ServicePoint]:
        result = await self.db.execute(
            select(ServicePoint).where(ServicePoint.business_id == business_id).order_by(ServicePoint.code)
        )
        return list(result.scalars().all())

    async def set_active(self, point: ServicePoint, *, active: bool) -> ServicePoint:
        point.active = active
        await self.db.commit()
        await self.db.refresh(point)
        return point
