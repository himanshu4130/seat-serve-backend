import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.qr import QRCode, QRStatus
from app.repositories.qr_repository import QRCodeRepository
from app.repositories.service_point_repository import ServicePointRepository


class QRService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.qr_codes = QRCodeRepository(db)
        self.points = ServicePointRepository(db)

    async def _unique_slug(self) -> str:
        for _ in range(5):
            slug = secrets.token_urlsafe(6).rstrip("=").replace("_", "").replace("-", "")[:8]
            if await self.qr_codes.get_by_slug(slug) is None:
                return slug
        # Exceedingly unlikely with an 8-char base64 alphabet, but fail loudly
        # rather than ever hand out a colliding slug.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate a unique QR slug")

    async def create_for_service_point(self, *, business_id: uuid.UUID, service_point_id: uuid.UUID) -> QRCode:
        point = await self.points.get(service_point_id)
        if point is None or point.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service point not found")
        existing = await self.qr_codes.get_by_service_point(service_point_id)
        if existing is not None:
            return existing
        slug = await self._unique_slug()
        return await self.qr_codes.create(business_id=business_id, service_point_id=service_point_id, slug=slug)

    async def list_for_business(self, business_id: uuid.UUID) -> list[QRCode]:
        return await self.qr_codes.list_for_business(business_id)

    async def get_by_slug(self, slug: str) -> QRCode:
        qr_code = await self.qr_codes.get_by_slug(slug)
        if qr_code is None or qr_code.status != QRStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found or disabled")
        return qr_code

    async def set_status(self, *, business_id: uuid.UUID, qr_code_id: uuid.UUID, status_: QRStatus) -> QRCode:
        qr_code = await self.qr_codes.get(qr_code_id)
        if qr_code is None or qr_code.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not found")
        return await self.qr_codes.set_status(qr_code, status=status_)
