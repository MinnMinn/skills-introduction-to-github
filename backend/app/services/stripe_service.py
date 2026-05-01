"""
Thin wrapper around the Stripe Python SDK.

PCI controls:
  - We never accept or log raw card numbers.
  - The SDK tokenises the card client-side; we receive only payment_method_id.
  - Webhook signature verification is enforced before any processing.
"""
import logging
from typing import Optional

import stripe
from stripe import StripeError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _init_stripe() -> None:
    settings = get_settings()
    if not stripe.api_key:
        stripe.api_key = settings.STRIPE_SECRET_KEY


# ── PaymentIntent helpers ─────────────────────────────────────────────────────

def create_payment_intent(
    amount: int,
    currency: str,
    customer_id: str,
    idempotency_key: str,
    payment_method_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> stripe.PaymentIntent:
    """
    Create a Stripe PaymentIntent.

    Uses the Stripe idempotency key header so that retrying the same
    request returns the existing PaymentIntent without creating a new charge.
    """
    _init_stripe()
    params: dict = {
        "amount": amount,
        "currency": currency.lower(),
        "metadata": {
            **(metadata or {}),
            # Store masked customer ref only — no PII
            "customer_ref": customer_id[:4] + "****",
        },
        "automatic_payment_methods": {"enabled": True},
    }
    if payment_method_id:
        params["payment_method"] = payment_method_id

    try:
        intent = stripe.PaymentIntent.create(
            **params,
            idempotency_key=idempotency_key,
        )
        logger.info("PaymentIntent created: %s status=%s", intent.id, intent.status)
        return intent
    except StripeError as exc:
        logger.error("Stripe error creating PaymentIntent: %s", exc.user_message)
        raise


def retrieve_payment_intent(intent_id: str) -> stripe.PaymentIntent:
    """Retrieve a PaymentIntent by ID."""
    _init_stripe()
    return stripe.PaymentIntent.retrieve(intent_id)


# ── Webhook verification ──────────────────────────────────────────────────────

def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """
    Verify the Stripe-Signature header and parse the event.

    Raises stripe.error.SignatureVerificationError (→ HTTP 401) if invalid.
    MANDATORY — must be called before any event processing.
    """
    settings = get_settings()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
