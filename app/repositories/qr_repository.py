import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qr import QRCode, QRStatus


class QRCodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, business_id: uuid.UUID, service_point_id: uuid.UUID, slug: str) -> QRCode:
        qr_code = QRCode(business_id=business_id, service_point_id=service_point_id, slug=slug)
        self.db.add(qr_code)
        await self.db.commit()
        await self.db.refresh(qr_code)
        return qr_code

    async def get(self, qr_code_id: uuid.UUID) -> QRCode | None:
        return await self.db.get(QRCode, qr_code_id)

    async def get_by_slug(self, slug: str) -> QRCode | None:
        result = await self.db.execute(select(QRCode).where(QRCode.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_service_point(self, service_point_id: uuid.UUID) -> QRCode | None:
        result = await self.db.execute(select(QRCode).where(QRCode.service_point_id == service_point_id))
        return result.scalar_one_or_none()

    async def list_for_business(self, business_id: uuid.UUID) -> list[QRCode]:
        result = await self.db.execute(select(QRCode).where(QRCode.business_id == business_id))
        return list(result.scalars().all())

    async def set_status(self, qr_code: QRCode, *, status: QRStatus) -> QRCode:
        qr_code.status = status
        await self.db.commit()
        await self.db.refresh(qr_code)
        return qr_code

    async def delete(self, qr_code: QRCode) -> None:
        await self.db.delete(qr_code)
        await self.db.commit()
