import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.order import Order, OrderStatus
from app.models.tenant import Tenant
from app.repositories.order_repository import OrderRepository
from app.schemas.analytics import AnalyticsSummaryOut, HourlyBucketOut, PlatformAnalyticsOut, TopProductOut

_EXCLUDED_FROM_REVENUE = {OrderStatus.CANCELLED, OrderStatus.REFUNDED}


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.orders = OrderRepository(db)

    async def business_summary(
        self,
        business_id: uuid.UUID,
        *,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> AnalyticsSummaryOut:
        orders = await self.orders.list_for_business(
            business_id, created_after=created_after, created_before=created_before
        )

        revenue_orders = [o for o in orders if o.paid and o.status not in _EXCLUDED_FROM_REVENUE]
        revenue = sum((Decimal(str(o.total)) for o in revenue_orders), Decimal("0"))
        order_count = len(orders)
        average_order_value = (revenue / len(revenue_orders)) if revenue_orders else Decimal("0")

        # top_products reflects demand (what was ordered, kitchen-relevant)
        # so it counts every non-cancelled/refunded order regardless of
        # payment timing. hourly's *revenue* column must mean the same thing
        # "revenue" means everywhere else in this summary — money actually
        # collected — so, unlike order_count, it only counts paid orders.
        product_totals: dict[str, list] = defaultdict(lambda: [0, Decimal("0")])
        hourly_totals: dict[int, list] = defaultdict(lambda: [0, Decimal("0")])
        for order in orders:
            if order.status in _EXCLUDED_FROM_REVENUE:
                continue
            hour_bucket = hourly_totals[order.created_at.hour]
            hour_bucket[0] += 1
            if order.paid:
                hour_bucket[1] += Decimal(str(order.total))
            for item in order.items:
                entry = product_totals[item.name]
                entry[0] += item.quantity
                entry[1] += Decimal(str(item.line_total))

        top_products = sorted(
            (TopProductOut(name=name, quantity_sold=qty, revenue=rev) for name, (qty, rev) in product_totals.items()),
            key=lambda p: p.quantity_sold,
            reverse=True,
        )[:5]
        hourly = sorted(
            (HourlyBucketOut(hour=hour, order_count=count, revenue=rev) for hour, (count, rev) in hourly_totals.items()),
            key=lambda h: h.hour,
        )

        return AnalyticsSummaryOut(
            order_count=order_count,
            revenue=revenue,
            average_order_value=average_order_value,
            top_products=top_products,
            hourly=hourly,
        )

    async def platform_summary(self) -> PlatformAnalyticsOut:
        tenant_count = (await self.db.execute(select(func.count()).select_from(Tenant))).scalar_one()
        business_count = (await self.db.execute(select(func.count()).select_from(Business))).scalar_one()
        order_count = (await self.db.execute(select(func.count()).select_from(Order))).scalar_one()

        result = await self.db.execute(
            select(Order.total).where(Order.paid.is_(True), Order.status.notin_(_EXCLUDED_FROM_REVENUE))
        )
        revenue = sum((Decimal(str(total)) for total in result.scalars().all()), Decimal("0"))

        return PlatformAnalyticsOut(
            tenant_count=tenant_count, business_count=business_count, order_count=order_count, revenue=revenue
        )
