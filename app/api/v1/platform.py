from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_analytics_service, get_business_service, require_platform_admin
from app.core.db import get_db
from app.repositories.tenant_repository import TenantRepository
from app.schemas.analytics import PlatformAnalyticsOut
from app.schemas.business import BusinessOut
from app.schemas.tenant import TenantOut
from app.services.analytics_service import AnalyticsService
from app.services.business_service import BusinessService

router = APIRouter(dependencies=[Depends(require_platform_admin)])


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(db: AsyncSession = Depends(get_db)) -> list[TenantOut]:
    tenants = await TenantRepository(db).list_all()
    return [TenantOut.model_validate(t) for t in tenants]


@router.get("/businesses", response_model=list[BusinessOut])
async def list_all_businesses(service: BusinessService = Depends(get_business_service)) -> list[BusinessOut]:
    businesses = await service.businesses.list_all()
    return [BusinessOut.model_validate(b) for b in businesses]


@router.get("/analytics", response_model=PlatformAnalyticsOut)
async def platform_analytics(service: AnalyticsService = Depends(get_analytics_service)) -> PlatformAnalyticsOut:
    return await service.platform_summary()
