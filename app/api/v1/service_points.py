import uuid

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import get_service_point_service, require_business_permission
from app.core.permissions import Permission
from app.schemas.service_point import (
    ServiceAreaCreate,
    ServiceAreaOut,
    ServicePointCreate,
    ServicePointOut,
    ServicePointStatusUpdate,
)
from app.services.service_point_service import ServicePointService

router = APIRouter()


@router.get("/areas", response_model=list[ServiceAreaOut])
async def list_areas(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: ServicePointService = Depends(get_service_point_service),
) -> list[ServiceAreaOut]:
    areas = await service.list_areas(business_id)
    return [ServiceAreaOut.model_validate(a) for a in areas]


@router.post("/areas", response_model=ServiceAreaOut, status_code=status.HTTP_201_CREATED)
async def create_area(
    business_id: uuid.UUID,
    payload: ServiceAreaCreate,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: ServicePointService = Depends(get_service_point_service),
) -> ServiceAreaOut:
    area = await service.create_area(business_id=business_id, name=payload.name)
    return ServiceAreaOut.model_validate(area)


@router.get("/points", response_model=list[ServicePointOut])
async def list_points(
    business_id: uuid.UUID,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: ServicePointService = Depends(get_service_point_service),
) -> list[ServicePointOut]:
    points = await service.list_points(business_id)
    return [ServicePointOut.model_validate(p) for p in points]


@router.post("/points", response_model=ServicePointOut, status_code=status.HTTP_201_CREATED)
async def create_point(
    business_id: uuid.UUID,
    payload: ServicePointCreate,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: ServicePointService = Depends(get_service_point_service),
) -> ServicePointOut:
    point = await service.create_point(
        business_id=business_id, area_id=payload.area_id, code=payload.code, kind=payload.kind, label=payload.label
    )
    return ServicePointOut.model_validate(point)


@router.patch("/points/{point_id}", response_model=ServicePointOut)
async def set_point_active(
    business_id: uuid.UUID,
    point_id: uuid.UUID,
    payload: ServicePointStatusUpdate,
    _=Depends(require_business_permission(Permission.QR_MANAGE)),
    service: ServicePointService = Depends(get_service_point_service),
) -> ServicePointOut:
    point = await service.set_active(business_id=business_id, point_id=point_id, active=payload.active)
    return ServicePointOut.model_validate(point)
