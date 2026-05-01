"""
Pydantic models for the payments domain.

PCI note: raw card numbers (PAN) never appear in these models.
We only deal with Stripe's payment_method_id / payment_intent_id.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


# ── Request / Response models ─────────────────────────────────────────────────

class CreatePaymentIntentRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit (e.g. cents)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO-4217 currency code")
    customer_id: str = Field(..., description="Internal customer identifier")
    idempotency_key: str = Field(..., min_length=16, max_length=128,
                                  description="Client-supplied idempotency key (UUID recommended)")
    payment_method_id: Optional[str] = Field(None, description="Stripe payment_method_id (tokenised by SDK)")
    metadata: dict = Field(default_factory=dict, description="Arbitrary metadata (no PAN allowed)")

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator("metadata")
    @classmethod
    def no_raw_card_data(cls, v: dict) -> dict:
        forbidden = {"card_number", "cvv", "pan", "full_card"}
        if forbidden.intersection(v.keys()):
            raise ValueError("Raw card data must not be included in metadata")
        return v


class CreatePaymentIntentResponse(BaseModel):
    payment_id: str
    client_secret: str  # Stripe PaymentIntent client_secret — sent to mobile SDK
    status: PaymentStatus
    amount: int
    currency: str
    idempotent: bool = Field(False, description="True when an existing intent was returned")


class PaymentRecord(BaseModel):
    """Internal representation stored in DynamoDB."""
    payment_id: str
    intent_id: str           # Stripe PaymentIntent ID
    user_id: str
    customer_id_masked: str  # first-4 chars + ****
    amount: int
    currency: str
    status: PaymentStatus
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    stripe_metadata: dict = Field(default_factory=dict)

    @classmethod
    def mask_customer_id(cls, customer_id: str) -> str:
        """Retain only first 4 chars — no PII in logs."""
        return customer_id[:4] + "****" if len(customer_id) > 4 else "****"


class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    amount: int
    currency: str
    created_at: datetime
    updated_at: datetime
    # customer_id is intentionally masked in the response
    customer_id_masked: str


class WebhookProcessResult(BaseModel):
    processed: bool
    event_type: str
    payment_id: Optional[str] = None
    message: str = ""
