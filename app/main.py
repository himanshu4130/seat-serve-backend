from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    analytics,
    billing,
    businesses,
    health,
    me,
    menu,
    orders,
    payments,
    platform,
    public,
    qr,
    service_points,
    staff,
    webhooks,
)
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SeatServe API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(me.router, prefix="/api/v1", tags=["me"])
    app.include_router(businesses.router, prefix="/api/v1/businesses", tags=["businesses"])
    app.include_router(menu.router, prefix="/api/v1/businesses/{business_id}/menu", tags=["menu"])
    app.include_router(
        service_points.router, prefix="/api/v1/businesses/{business_id}/service", tags=["service-points"]
    )
    app.include_router(qr.router, prefix="/api/v1/businesses/{business_id}/qr-codes", tags=["qr"])
    app.include_router(orders.router, prefix="/api/v1/businesses/{business_id}/orders", tags=["orders"])
    app.include_router(staff.router, prefix="/api/v1/businesses/{business_id}/staff", tags=["staff"])
    app.include_router(
        payments.router, prefix="/api/v1/businesses/{business_id}/payments", tags=["payments"]
    )
    app.include_router(
        billing.router, prefix="/api/v1/businesses/{business_id}/billing", tags=["billing"]
    )
    app.include_router(billing.plans_router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(
        analytics.router, prefix="/api/v1/businesses/{business_id}/analytics", tags=["analytics"]
    )
    app.include_router(platform.router, prefix="/api/v1/platform", tags=["platform"])
    app.include_router(public.router, prefix="/api/v1/public", tags=["public"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    return app


app = create_app()
