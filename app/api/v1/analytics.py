import uuid
from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_analytics_service, require_business_permission
from app.core.permissions import Permission
from app.schemas.analytics import AnalyticsSummaryOut
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummaryOut)
async def get_summary(
    business_id: uuid.UUID,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    _=Depends(require_business_permission(Permission.REPORTS_VIEW)),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummaryOut:
    return await service.business_summary(business_id, created_after=created_after, created_before=created_before)
