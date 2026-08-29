import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, Plan, PlanId, Subscription
from app.models.business import SubscriptionState
from app.repositories.billing_repository import InvoiceRepository, PlanRepository, SubscriptionRepository
from app.repositories.business_repository import BusinessRepository
from app.repositories.payment_repository import PaymentTransactionRepository
from app.models.payment import PaymentProviderName, PaymentPurpose
from app.services.payments.base import PaymentProvider, PaymentProviderError


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plans = PlanRepository(db)
        self.subscriptions = SubscriptionRepository(db)
        self.invoices = InvoiceRepository(db)
        self.businesses = BusinessRepository(db)
        self.transactions = PaymentTransactionRepository(db)

    async def list_plans(self) -> list[Plan]:
        return await self.plans.list_all()

    async def get_subscription(self, business_id: uuid.UUID) -> Subscription:
        subscription = await self.subscriptions.get_for_business(business_id)
        if subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription for this business")
        return subscription

    async def set_plan(self, *, business_id: uuid.UUID, plan_id: PlanId) -> Subscription:
        if await self.plans.get(plan_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown plan")
        subscription = await self.get_subscription(business_id)
        return await self.subscriptions.set_plan(subscription, plan_id=plan_id)

    async def _sync_business_subscription_state(self, business_id: uuid.UUID, state: SubscriptionState) -> None:
        # Business.subscription_state is a denormalized read-model column —
        # Subscription.state is canonical and always wins.
        business = await self.businesses.get(business_id)
        if business is not None and business.subscription_state != state:
            business.subscription_state = state
            await self.db.commit()

    async def set_subscription_state(self, *, business_id: uuid.UUID, state: SubscriptionState) -> Subscription:
        subscription = await self.get_subscription(business_id)
        subscription = await self.subscriptions.set_state(subscription, state=state)
        await self._sync_business_subscription_state(business_id, state)
        return subscription

    async def list_invoices(self, business_id: uuid.UUID) -> list[Invoice]:
        return await self.invoices.list_for_business(business_id)

    async def _get_invoice_for_business(self, *, business_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
        invoice = await self.invoices.get(invoice_id)
        if invoice is None or invoice.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return invoice

    async def create_invoice_payment(self, *, business_id: uuid.UUID, invoice_id: uuid.UUID, provider: PaymentProvider):
        invoice = await self._get_invoice_for_business(business_id=business_id, invoice_id=invoice_id)
        if invoice.status.value == "PAID":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already paid")

        transaction = await self.transactions.create(
            business_id=business_id,
            purpose=PaymentPurpose.SUBSCRIPTION_INVOICE,
            provider=PaymentProviderName.RAZORPAY,
            amount=invoice.amount,
            invoice_id=invoice.id,
        )
        try:
            provider_order = await provider.create_order(
                amount=invoice.amount, currency="INR", receipt=f"invoice-{invoice.id}"
            )
        except PaymentProviderError as exc:
            await self.transactions.mark_failed(transaction, reason=str(exc))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        transaction = await self.transactions.set_provider_order(
            transaction, provider_order_id=provider_order.provider_order_id
        )
        return transaction, provider_order
