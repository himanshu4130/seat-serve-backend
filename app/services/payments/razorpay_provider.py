import hashlib
import hmac

import httpx

from app.services.payments.base import (
    PaymentProvider,
    PaymentProviderError,
    ProviderOrder,
    ProviderRefund,
)

_API_BASE = "https://api.razorpay.com/v1"


def _to_minor_units(amount: float) -> int:
    """Razorpay amounts are integers in the smallest currency unit (paise for
    INR). Round to cents/paise via string formatting to dodge float drift."""
    return int(round(float(amount) * 100))


class RazorpayProvider(PaymentProvider):
    def __init__(self, *, key_id: str, key_secret: str, webhook_secret: str):
        if not key_id or not key_secret:
            raise PaymentProviderError("Razorpay is not configured (missing key id/secret)")
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret

    async def create_order(self, *, amount: float, currency: str, receipt: str) -> ProviderOrder:
        amount_minor = _to_minor_units(amount)
        async with httpx.AsyncClient(auth=(self._key_id, self._key_secret), timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{_API_BASE}/orders",
                    json={
                        "amount": amount_minor,
                        "currency": currency,
                        "receipt": receipt,
                        "payment_capture": 1,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise PaymentProviderError(f"Razorpay order creation failed: {exc}") from exc

        body = response.json()
        return ProviderOrder(
            provider_order_id=body["id"],
            amount_minor=body["amount"],
            currency=body["currency"],
            key_id=self._key_id,
        )

    def verify_payment_signature(
        self, *, provider_order_id: str, provider_payment_id: str, signature: str
    ) -> bool:
        # Per Razorpay docs: HMAC-SHA256 of "{order_id}|{payment_id}" signed
        # with the key secret must equal the signature the client hands back.
        payload = f"{provider_order_id}|{provider_payment_id}".encode()
        expected = hmac.new(self._key_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            return False
        expected = hmac.new(self._webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def create_refund(self, *, provider_payment_id: str, amount: float) -> ProviderRefund:
        amount_minor = _to_minor_units(amount)
        async with httpx.AsyncClient(auth=(self._key_id, self._key_secret), timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{_API_BASE}/payments/{provider_payment_id}/refund",
                    json={"amount": amount_minor},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise PaymentProviderError(f"Razorpay refund failed: {exc}") from exc

        body = response.json()
        return ProviderRefund(provider_refund_id=body["id"], status=body.get("status", "processed"))
