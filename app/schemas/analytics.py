from decimal import Decimal

from pydantic import BaseModel


class TopProductOut(BaseModel):
    name: str
    quantity_sold: int
    revenue: Decimal


class HourlyBucketOut(BaseModel):
    hour: int  # 0-23, local to UTC
    order_count: int
    revenue: Decimal


class AnalyticsSummaryOut(BaseModel):
    order_count: int
    revenue: Decimal
    average_order_value: Decimal
    top_products: list[TopProductOut]
    hourly: list[HourlyBucketOut]


class PlatformAnalyticsOut(BaseModel):
    tenant_count: int
    business_count: int
    order_count: int
    revenue: Decimal
