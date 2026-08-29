import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, InvoiceStatus, Plan, PlanId, Subscription
from app.models.business import SubscriptionState


class PlanRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Plan]:
        result = await self.db.execute(select(Plan))
        return list(result.scalars().all())

    async def get(self, plan_id: PlanId) -> Plan | None:
        return await self.db.get(Plan, plan_id)


class SubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, business_id: uuid.UUID, plan_id: PlanId, state: SubscriptionState = SubscriptionState.TRIAL
    ) -> Subscription:
        subscription = Subscription(business_id=business_id, plan_id=plan_id, state=state)
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def get_for_business(self, business_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(select(Subscription).where(Subscription.business_id == business_id))
        return result.scalar_one_or_none()

    async def set_plan(self, subscription: Subscription, *, plan_id: PlanId) -> Subscription:
        subscription.plan_id = plan_id
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def set_state(self, subscription: Subscription, *, state: SubscriptionState) -> Subscription:
        subscription.state = state
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription


class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, business_id: uuid.UUID, subscription_id: uuid.UUID, amount: float
    ) -> Invoice:
        invoice = Invoice(business_id=business_id, subscription_id=subscription_id, amount=amount)
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self.db.get(Invoice, invoice_id)

    async def list_for_business(self, business_id: uuid.UUID) -> list[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(Invoice.business_id == business_id).order_by(Invoice.issued_at.desc())
        )
        return list(result.scalars().all())

    async def mark_paid(self, invoice: Invoice) -> Invoice:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice
