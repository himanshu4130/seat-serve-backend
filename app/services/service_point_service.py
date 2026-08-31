import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_point import ServiceArea, ServicePoint, ServicePointKind
from app.repositories.qr_repository import QRCodeRepository
from app.repositories.service_point_repository import ServiceAreaRepository, ServicePointRepository


class ServicePointService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.areas = ServiceAreaRepository(db)
        self.points = ServicePointRepository(db)
        self.qr_codes = QRCodeRepository(db)

    async def create_area(self, *, business_id: uuid.UUID, name: str) -> ServiceArea:
        return await self.areas.create(business_id=business_id, name=name)

    async def list_areas(self, business_id: uuid.UUID) -> list[ServiceArea]:
        return await self.areas.list_for_business(business_id)

    async def update_area(self, *, business_id: uuid.UUID, area_id: uuid.UUID, name: str) -> ServiceArea:
        area = await self.areas.get(area_id)
        if area is None or area.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service area not found")
        return await self.areas.update(area, name=name)

    async def delete_area(self, *, business_id: uuid.UUID, area_id: uuid.UUID) -> None:
        area = await self.areas.get(area_id)
        if area is None or area.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service area not found")
        
        # Delete all service points in this area first (and their QR codes) in a single transaction
        points = await self.points.list_for_area(area_id)
        for point in points:
            # Delete QR code first
            qr_code = await self.qr_codes.get_by_service_point(point.id)
            if qr_code:
                await self.db.delete(qr_code)
            # Then delete the service point
            await self.db.delete(point)
        
        # Delete the area
        await self.db.delete(area)
        
        # Single commit for all deletions
        await self.db.commit()

    async def create_point(
        self, *, business_id: uuid.UUID, area_id: uuid.UUID, code: str, kind: ServicePointKind, label: str
    ) -> ServicePoint:
        area = await self.areas.get(area_id)
        if area is None or area.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service area not found")
        return await self.points.create(business_id=business_id, area_id=area_id, code=code, kind=kind, label=label)

    async def list_points(self, business_id: uuid.UUID) -> list[ServicePoint]:
        return await self.points.list_for_business(business_id)

    async def get_point_for_business(self, *, business_id: uuid.UUID, point_id: uuid.UUID) -> ServicePoint:
        point = await self.points.get(point_id)
        if point is None or point.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service point not found")
        return point

    async def set_active(self, *, business_id: uuid.UUID, point_id: uuid.UUID, active: bool) -> ServicePoint:
        point = await self.get_point_for_business(business_id=business_id, point_id=point_id)
        return await self.points.set_active(point, active=active)

    async def update_point(
        self, *, business_id: uuid.UUID, point_id: uuid.UUID, code: str, area_id: uuid.UUID, kind: ServicePointKind, label: str
    ) -> ServicePoint:
        point = await self.get_point_for_business(business_id=business_id, point_id=point_id)
        return await self.points.update(point, code=code, area_id=area_id, kind=kind, label=label)

    async def delete_point(self, *, business_id: uuid.UUID, point_id: uuid.UUID) -> None:
        point = await self.get_point_for_business(business_id=business_id, point_id=point_id)
        
        # Delete QR code first
        qr_code = await self.qr_codes.get_by_service_point(point.id)
        if qr_code:
            await self.db.delete(qr_code)
        
        # Then delete the service point
        await self.db.delete(point)
        
        # Single commit for both deletions
        await self.db.commit()
