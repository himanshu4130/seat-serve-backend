import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import (
    PaymentConfig,
    PaymentConnectionStatus,
    PaymentMethod,
    PaymentProviderName,
    PaymentPurpose,
    PaymentStatus,
    PaymentTransaction,
    PaymentWebhookEvent,
    Refund,
    RefundStatus,
)


class PaymentConfigRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_for_business(self, business_id: uuid.UUID) -> PaymentConfig | None:
        result = await self.db.execute(select(PaymentConfig).where(PaymentConfig.business_id == business_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, business_id: uuid.UUID) -> PaymentConfig:
        config = await self.get_for_business(business_id)
        if config is not None:
            return config
        config = PaymentConfig(business_id=business_id)
        self.db.add(config)
        try:
            await self.db.commit()
        except IntegrityError:
            # Lost a create race — another request created it first.
            await self.db.rollback()
            config = await self.get_for_business(business_id)
            assert config is not None
            return config
        await self.db.refresh(config)
        return config

    async def update_status(self, config: PaymentConfig, *, status: PaymentConnectionStatus) -> PaymentConfig:
        config.status = status
        await self.db.commit()
        await self.db.refresh(config)
        return config


class PaymentTransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        business_id: uuid.UUID,
        purpose: PaymentPurpose,
        provider: PaymentProviderName,
        amount: float,
        currency: str = "INR",
        order_id: uuid.UUID | None = None,
        invoice_id: uuid.UUID | None = None,
    ) -> PaymentTransaction:
        transaction = PaymentTransaction(
            business_id=business_id,
            purpose=purpose,
            provider=provider,
            amount=amount,
            currency=currency,
            order_id=order_id,
            invoice_id=invoice_id,
            status=PaymentStatus.CREATING,
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def get(self, transaction_id: uuid.UUID) -> PaymentTransaction | None:
        return await self.db.get(PaymentTransaction, transaction_id)

    async def get_by_provider_order_id(self, provider_order_id: str) -> PaymentTransaction | None:
        result = await self.db.execute(
            select(PaymentTransaction).where(PaymentTransaction.provider_order_id == provider_order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> PaymentTransaction | None:
        result = await self.db.execute(
            select(PaymentTransaction).where(PaymentTransaction.provider_payment_id == provider_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_successful_for_order(self, order_id: uuid.UUID) -> PaymentTransaction | None:
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.order_id == order_id, PaymentTransaction.status == PaymentStatus.SUCCESS
            )
        )
        return result.scalar_one_or_none()

    async def list_for_business(self, business_id: uuid.UUID) -> list[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.business_id == business_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_provider_order(self, transaction: PaymentTransaction, *, provider_order_id: str) -> PaymentTransaction:
        transaction.provider_order_id = provider_order_id
        transaction.status = PaymentStatus.WAITING
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def mark_success(
        self,
        transaction: PaymentTransaction,
        *,
        provider_payment_id: str,
        method: PaymentMethod | None = None,
    ) -> PaymentTransaction:
        transaction.provider_payment_id = provider_payment_id
        transaction.status = PaymentStatus.SUCCESS
        if method is not None:
            transaction.method = method
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def mark_failed(self, transaction: PaymentTransaction, *, reason: str) -> PaymentTransaction:
        transaction.status = PaymentStatus.FAILED
        transaction.failure_reason = reason
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def mark_refunded(self, transaction: PaymentTransaction) -> PaymentTransaction:
        transaction.status = PaymentStatus.REFUNDED
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction


class RefundRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, transaction_id: uuid.UUID, amount: float, reason: str) -> Refund:
        refund = Refund(transaction_id=transaction_id, amount=amount, reason=reason)
        self.db.add(refund)
        await self.db.commit()
        await self.db.refresh(refund)
        return refund

    async def mark_processed(self, refund: Refund, *, provider_refund_id: str) -> Refund:
        refund.status = RefundStatus.PROCESSED
        refund.provider_refund_id = provider_refund_id
        await self.db.commit()
        await self.db.refresh(refund)
        return refund

    async def mark_failed(self, refund: Refund) -> Refund:
        refund.status = RefundStatus.FAILED
        await self.db.commit()
        await self.db.refresh(refund)
        return refund


class WebhookEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def already_processed(self, *, provider: PaymentProviderName, provider_event_id: str) -> bool:
        result = await self.db.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.provider == provider,
                PaymentWebhookEvent.provider_event_id == provider_event_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def record(
        self,
        *,
        provider: PaymentProviderName,
        provider_event_id: str,
        event_type: str,
        signature_valid: bool,
        payload: str,
    ) -> PaymentWebhookEvent:
        event = PaymentWebhookEvent(
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            signature_valid=signature_valid,
            payload=payload,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
