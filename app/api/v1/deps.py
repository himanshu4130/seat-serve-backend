import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.permissions import Permission, role_has_permission
from app.core.security import get_current_user, get_current_platform_admin
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.services.billing_service import BillingService
from app.services.business_service import BusinessService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.payments import build_payment_provider
from app.services.payments.base import PaymentProvider, PaymentProviderError
from app.services.qr_service import QRService
from app.services.service_point_service import ServicePointService
from app.services.staff_service import StaffService

__all__ = [
    "get_current_user",
    "get_business_service",
    "get_menu_service",
    "get_service_point_service",
    "get_qr_service",
    "get_order_service",
    "get_staff_service",
    "get_payment_service",
    "get_billing_service",
    "get_analytics_service",
    "get_payment_provider",
    "require_business_permission",
    "require_platform_admin",
]


def get_business_service(db: AsyncSession = Depends(get_db)) -> BusinessService:
    return BusinessService(db)


def get_menu_service(db: AsyncSession = Depends(get_db)) -> MenuService:
    return MenuService(db)


def get_service_point_service(db: AsyncSession = Depends(get_db)) -> ServicePointService:
    return ServicePointService(db)


def get_qr_service(db: AsyncSession = Depends(get_db)) -> QRService:
    return QRService(db)


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


def get_staff_service(db: AsyncSession = Depends(get_db)) -> StaffService:
    return StaffService(db)


def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


def get_billing_service(db: AsyncSession = Depends(get_db)) -> BillingService:
    return BillingService(db)


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


def get_payment_provider(settings: Settings = Depends(get_settings)) -> PaymentProvider:
    """Only routes that actually call out to Razorpay (create order, refund)
    depend on this — reading config/transactions never needs a live provider."""
    try:
        return build_payment_provider(settings)
    except PaymentProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


def require_business_permission(permission: Permission):
    """Dependency factory for routes with a `business_id` path param — later
    phases' routers (menu, orders, ...) depend on this the same way."""

    async def dependency(
        business_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        service: BusinessService = Depends(get_business_service),
    ) -> User:
        role = await service.get_role_for_user(current_user=current_user, business_id=business_id)
        if role is None or not role_has_permission(role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return current_user

    return dependency


async def require_platform_admin(current_user: User = Depends(get_current_platform_admin)) -> User:
    return current_user
