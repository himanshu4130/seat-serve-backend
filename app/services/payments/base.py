from abc import ABC, abstractmethod
from dataclasses import dataclass


class PaymentProviderError(Exception):
    """Raised for any provider-side failure: not configured, network error,
    or the provider's API rejecting the request. Callers turn this into a
    502/503 at the API boundary — it is never swallowed into a fake success."""


@dataclass
class ProviderOrder:
    provider_order_id: str
    amount_minor: int  # smallest currency unit (e.g. paise)
    currency: str
    key_id: str  # public key the frontend checkout widget needs to open the payment sheet


@dataclass
class ProviderRefund:
    provider_refund_id: str
    status: str


class PaymentProvider(ABC):
    """Provider-agnostic contract. Concrete implementation (RazorpayProvider)
    lives beside this; a new provider is a new class implementing this same
    interface, never a branch inside the service layer."""

    @abstractmethod
    async def create_order(self, *, amount: float, currency: str, receipt: str) -> ProviderOrder: ...

    @abstractmethod
    def verify_payment_signature(
        self, *, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool: ...

    @abstractmethod
    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool: ...

    @abstractmethod
    async def create_refund(self, *, provider_payment_id: str, amount: float) -> ProviderRefund: ...
