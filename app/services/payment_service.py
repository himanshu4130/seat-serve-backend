import hashlib
import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.order import OrderStatus
from app.models.payment import (
    PaymentConfig,
    PaymentConnectionStatus,
    PaymentProviderName,
    PaymentPurpose,
    PaymentStatus,
    PaymentTransaction,
    Refund,
)
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import (
    PaymentConfigRepository,
    PaymentTransactionRepository,
    RefundRepository,
    WebhookEventRepository,
)
from app.services.order_service import OrderService
from app.services.payments.base import PaymentProvider, PaymentProviderError, ProviderOrder


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.configs = PaymentConfigRepository(db)
        self.transactions = PaymentTransactionRepository(db)
        self.refunds = RefundRepository(db)
        self.webhook_events = WebhookEventRepository(db)
        self.orders = OrderRepository(db)
        self.order_service = OrderService(db)

    async def get_config(self, *, business_id: uuid.UUID, settings: Settings) -> PaymentConfig:
        config = await self.configs.get_or_create(business_id)
        desired = (
            PaymentConnectionStatus.CONNECTED
            if settings.razorpay_configured
            else PaymentConnectionStatus.ACTION_REQUIRED
        )
        if config.status != desired:
            config = await self.configs.update_status(config, status=desired)
        return config

    async def create_order_payment(
        self, *, business_id: uuid.UUID, order_id: uuid.UUID, provider: PaymentProvider
    ) -> tuple[PaymentTransaction, ProviderOrder]:
        order = await self.orders.get(order_id)
        if order is None or order.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.paid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already paid")
        if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is no longer payable")

        transaction = await self.transactions.create(
            business_id=business_id,
            purpose=PaymentPurpose.ORDER,
            provider=PaymentProviderName.RAZORPAY,
            amount=order.total,
            order_id=order.id,
        )
        try:
            provider_order = await provider.create_order(
                amount=order.total, currency="INR", receipt=str(order.order_number)
            )
        except PaymentProviderError as exc:
            await self.transactions.mark_failed(transaction, reason=str(exc))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        transaction = await self.transactions.set_provider_order(
            transaction, provider_order_id=provider_order.provider_order_id
        )
        return transaction, provider_order

    async def verify_payment(
        self,
        *,
        transaction_id: uuid.UUID,
        provider_payment_id: str,
        provider_signature: str,
        provider: PaymentProvider,
    ) -> PaymentTransaction:
        transaction = await self.transactions.get(transaction_id)
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment transaction not found")
        if transaction.status == PaymentStatus.SUCCESS:
            # Idempotent: a duplicate/replayed verify call must never be able
            # to downgrade an already-settled payment back to FAILED.
            return transaction
        if transaction.provider_order_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment was never initiated")

        valid = provider.verify_payment_signature(
            provider_order_id=transaction.provider_order_id,
            provider_payment_id=provider_payment_id,
            signature=provider_signature,
        )
        if not valid:
            await self.transactions.mark_failed(transaction, reason="Signature verification failed")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment verification failed")

        transaction = await self.transactions.mark_success(transaction, provider_payment_id=provider_payment_id)
        await self._settle(transaction)
        return transaction

    async def _settle(self, transaction: PaymentTransaction) -> None:
        """Mark whatever this transaction paid for as paid, once and only
        once (idempotent — re-settling an already-paid order is a no-op)."""
        if transaction.purpose == PaymentPurpose.ORDER and transaction.order_id is not None:
            order = await self.orders.get(transaction.order_id)
            if order is not None and not order.paid:
                await self.orders.set_paid(order, paid=True)
        elif transaction.purpose == PaymentPurpose.SUBSCRIPTION_INVOICE and transaction.invoice_id is not None:
            from app.repositories.billing_repository import InvoiceRepository

            invoices = InvoiceRepository(self.db)
            invoice = await invoices.get(transaction.invoice_id)
            if invoice is not None and invoice.status != "PAID":
                await invoices.mark_paid(invoice)

    async def handle_webhook(self, *, raw_body: bytes, signature: str, provider: PaymentProvider) -> None:
        valid = provider.verify_webhook_signature(payload=raw_body, signature=signature)
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed webhook payload") from exc

        event_type = payload.get("event", "unknown")
        # Razorpay doesn't guarantee a stable top-level event id, so dedup on
        # the exact payload bytes — an identical redelivery is a safe no-op.
        event_id = hashlib.sha256(raw_body).hexdigest()

        already_processed = await self.webhook_events.already_processed(
            provider=PaymentProviderName.RAZORPAY, provider_event_id=event_id
        )
        if not already_processed:
            await self.webhook_events.record(
                provider=PaymentProviderName.RAZORPAY,
                provider_event_id=event_id,
                event_type=event_type,
                signature_valid=valid,
                payload=raw_body.decode(errors="replace"),
            )

        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

        if already_processed:
            return

        payload_entity = payload.get("payload", {})
        if event_type == "payment.captured":
            payment = payload_entity.get("payment", {}).get("entity", {})
            transaction = await self.transactions.get_by_provider_order_id(payment.get("order_id", ""))
            if transaction is not None and transaction.status.value != "SUCCESS":
                transaction = await self.transactions.mark_success(transaction, provider_payment_id=payment.get("id", ""))
                await self._settle(transaction)
        elif event_type == "payment.failed":
            payment = payload_entity.get("payment", {}).get("entity", {})
            transaction = await self.transactions.get_by_provider_order_id(payment.get("order_id", ""))
            if transaction is not None:
                await self.transactions.mark_failed(transaction, reason=payment.get("error_description", "Payment failed"))
        elif event_type == "refund.processed":
            refund_entity = payload_entity.get("refund", {}).get("entity", {})
            transaction = await self.transactions.get_by_provider_payment_id(refund_entity.get("payment_id", ""))
            if transaction is not None and transaction.status.value != "REFUNDED":
                await self.transactions.mark_refunded(transaction)
                if transaction.order_id is not None:
                    order = await self.orders.get(transaction.order_id)
                    if order is not None and order.status != OrderStatus.REFUNDED:
                        await self.order_service.set_status(
                            business_id=order.business_id, order_id=order.id, new_status=OrderStatus.REFUNDED
                        )

    async def create_refund(
        self, *, business_id: uuid.UUID, order_id: uuid.UUID, reason: str, provider: PaymentProvider
    ) -> Refund:
        order = await self.orders.get(order_id)
        if order is None or order.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if not order.paid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order was never paid")

        transaction = await self.transactions.get_successful_for_order(order_id)
        if transaction is None or transaction.provider_payment_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No successful payment to refund")

        refund_row = await self.refunds.create(transaction_id=transaction.id, amount=order.total, reason=reason)
        try:
            provider_refund = await provider.create_refund(
                provider_payment_id=transaction.provider_payment_id, amount=order.total
            )
        except PaymentProviderError as exc:
            await self.refunds.mark_failed(refund_row)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        refund_row = await self.refunds.mark_processed(refund_row, provider_refund_id=provider_refund.provider_refund_id)
        await self.transactions.mark_refunded(transaction)
        await self.order_service.set_status(business_id=business_id, order_id=order_id, new_status=OrderStatus.REFUNDED)
        return refund_row
