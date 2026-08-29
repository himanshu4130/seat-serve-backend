from app.core.config import Settings
from app.services.payments.base import PaymentProvider, PaymentProviderError
from app.services.payments.razorpay_provider import RazorpayProvider

__all__ = ["PaymentProvider", "PaymentProviderError", "build_payment_provider"]


def build_payment_provider(settings: Settings) -> PaymentProvider:
    """The only provider wired up today is Razorpay — the frontend's
    onboarding flow only ever offers Razorpay, and no other provider's
    credentials exist. Adding Stripe/PhonePe later is a new branch here plus
    a new class next to RazorpayProvider, nothing else changes."""
    if not settings.razorpay_configured:
        raise PaymentProviderError("No payment provider is configured")
    return RazorpayProvider(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        webhook_secret=settings.razorpay_webhook_secret,
    )
