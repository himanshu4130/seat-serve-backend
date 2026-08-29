import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_qr_service, require_business_permission
from app.core.permissions import Permission
from app.models.qr import QRStatus
from app.schemas.qr import QRCodeCreate, QRCodeOut
from app.services.qr_service import QRService

router = APIRouter()


@router.get("", response_model=list[QRCodeOut])
async def list_qr_codes(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: QRService = Depends(get_qr_service),
) -> list[QRCodeOut]:
    qr_codes = await service.list_for_business(business_id)
    return [QRCodeOut.model_validate(q) for q in qr_codes]


@router.post("", response_model=QRCodeOut, status_code=status.HTTP_201_CREATED)
async def create_qr_code(
    business_id: uuid.UUID,
    payload: QRCodeCreate,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: QRService = Depends(get_qr_service),
) -> QRCodeOut:
    qr_code = await service.create_for_service_point(business_id=business_id, service_point_id=payload.service_point_id)
    return QRCodeOut.model_validate(qr_code)


@router.post("/{qr_code_id}/disable", response_model=QRCodeOut)
async def disable_qr_code(
    business_id: uuid.UUID,
    qr_code_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: QRService = Depends(get_qr_service),
) -> QRCodeOut:
    qr_code = await service.set_status(business_id=business_id, qr_code_id=qr_code_id, status_=QRStatus.DISABLED)
    return QRCodeOut.model_validate(qr_code)


@router.post("/{qr_code_id}/enable", response_model=QRCodeOut)
async def enable_qr_code(
    business_id: uuid.UUID,
    qr_code_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: QRService = Depends(get_qr_service),
) -> QRCodeOut:
    qr_code = await service.set_status(business_id=business_id, qr_code_id=qr_code_id, status_=QRStatus.ACTIVE)
    return QRCodeOut.model_validate(qr_code)
