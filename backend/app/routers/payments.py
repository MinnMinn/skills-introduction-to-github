"""
Payment API routes.

Endpoints:
  POST /api/payments/create-intent  — create Stripe PaymentIntent (rate-limited 10/min)
  POST /api/payments/webhook        — Stripe webhook handler (sig-verified)
  GET  /api/payments/{payment_id}   — fetch payment status (user-scoped)
  GET  /api/payments/dashboard      — CS dashboard (all payments, masked PII)
"""
import logging
import uuid
from datetime import datetime, timezone

import stripe.error
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.models.payment import (
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    PaymentRecord,
    PaymentStatus,
    PaymentStatusResponse,
    WebhookProcessResult,
)
from app.services import cloudwatch_service, dynamodb_service, sns_service, stripe_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payments", tags=["payments"])


# ── Dependency: authenticated user ────────────────────────────────────────────

def get_current_user_id(request: Request) -> str:
    """
    Extract the authenticated user ID.

    In a real deployment this would validate a JWT / OAuth token.
    For this implementation we read from request.state (set by auth middleware)
    and fall back to a header for integration testing.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    # Fallback: X-User-ID header (integration tests / service-to-service)
    header_user = request.headers.get("X-User-ID")
    if header_user:
        return header_user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


# ── POST /api/payments/create-intent ─────────────────────────────────────────

@router.post(
    "/create-intent",
    response_model=CreatePaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Stripe PaymentIntent",
)
async def create_payment_intent(
    body: CreatePaymentIntentRequest,
    user_id: str = Depends(get_current_user_id),
) -> CreatePaymentIntentResponse:
    """
    Create a Stripe PaymentIntent and persist the record.

    - Idempotent: same idempotency_key returns the original intent.
    - Rate-limited: 10 requests/min per user (enforced by RateLimitMiddleware).
    - PCI: we never see or store raw card numbers.
    """
    logger.info(
        "create-intent request: user=%s amount=%d currency=%s",
        user_id, body.amount, body.currency,
    )

    # 1. Idempotency check
    existing_payment_id = dynamodb_service.claim_idempotency_key(
        body.idempotency_key, user_id
    )
    if existing_payment_id:
        existing = dynamodb_service.get_payment_by_id(existing_payment_id, user_id)
        if existing:
            logger.info("Idempotent hit: returning existing payment %s", existing_payment_id)
            intent = stripe_service.retrieve_payment_intent(existing.intent_id)
            return CreatePaymentIntentResponse(
                payment_id=existing.payment_id,
                client_secret=intent.client_secret,
                status=existing.status,
                amount=existing.amount,
                currency=existing.currency,
                idempotent=True,
            )

    # 2. Create Stripe PaymentIntent
    try:
        intent = stripe_service.create_payment_intent(
            amount=body.amount,
            currency=body.currency,
            customer_id=body.customer_id,
            idempotency_key=body.idempotency_key,
            payment_method_id=body.payment_method_id,
            metadata=body.metadata,
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe error: %s", exc.user_message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {exc.user_message}",
        )

    # 3. Persist payment record
    payment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    record = PaymentRecord(
        payment_id=payment_id,
        intent_id=intent.id,
        user_id=user_id,
        customer_id_masked=PaymentRecord.mask_customer_id(body.customer_id),
        amount=body.amount,
        currency=body.currency,
        status=PaymentStatus.PENDING,
        idempotency_key=body.idempotency_key,
        created_at=now,
        updated_at=now,
        stripe_metadata=dict(intent.metadata or {}),
    )
    dynamodb_service.create_payment_record(record)

    # 4. Link idempotency key → payment_id
    dynamodb_service.link_idempotency_key_to_payment(body.idempotency_key, payment_id)

    # 5. Audit log
    cloudwatch_service.audit_payment_transition(
        payment_id=payment_id,
        previous_status="none",
        new_status=PaymentStatus.PENDING.value,
        customer_id_masked=record.customer_id_masked,
        amount=body.amount,
        currency=body.currency,
        triggered_by="user",
        extra={"intent_id": intent.id},
    )

    # 6. Publish SNS event
    sns_service.publish_payment_event(
        event_type="payment.created",
        payment_id=payment_id,
        customer_id_masked=record.customer_id_masked,
        amount=body.amount,
        currency=body.currency,
        status=PaymentStatus.PENDING.value,
    )

    return CreatePaymentIntentResponse(
        payment_id=payment_id,
        client_secret=intent.client_secret,
        status=PaymentStatus.PENDING,
        amount=body.amount,
        currency=body.currency,
        idempotent=False,
    )


# ── POST /api/payments/webhook ────────────────────────────────────────────────

@router.post(
    "/webhook",
    response_model=WebhookProcessResult,
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook handler",
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> WebhookProcessResult:
    """
    Receive and process Stripe webhook events.

    Security: signature is verified BEFORE any processing.
    Returns 401 if signature is invalid — no DB write occurs.
    """
    raw_body = await request.body()

    # 1. Verify signature — MANDATORY
    try:
        event = stripe_service.construct_webhook_event(raw_body, stripe_signature)
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature — rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    event_type: str = event["type"]
    event_data = event["data"]["object"]

    logger.info("Received webhook event: %s id=%s", event_type, event.get("id"))

    # 2. Route event to handler
    handlers = {
        "payment_intent.succeeded": _handle_payment_succeeded,
        "payment_intent.payment_failed": _handle_payment_failed,
        "payment_intent.canceled": _handle_payment_canceled,
        "payment_intent.processing": _handle_payment_processing,
    }
    handler = handlers.get(event_type)
    if not handler:
        return WebhookProcessResult(
            processed=False,
            event_type=event_type,
            message="Event type not handled",
        )

    return await handler(event_data)


async def _handle_payment_succeeded(intent_data: dict) -> WebhookProcessResult:
    return await _update_payment_from_webhook(
        intent_data, PaymentStatus.SUCCEEDED, "payment.succeeded"
    )


async def _handle_payment_failed(intent_data: dict) -> WebhookProcessResult:
    return await _update_payment_from_webhook(
        intent_data, PaymentStatus.FAILED, "payment.failed"
    )


async def _handle_payment_canceled(intent_data: dict) -> WebhookProcessResult:
    return await _update_payment_from_webhook(
        intent_data, PaymentStatus.CANCELED, "payment.canceled"
    )


async def _handle_payment_processing(intent_data: dict) -> WebhookProcessResult:
    return await _update_payment_from_webhook(
        intent_data, PaymentStatus.PROCESSING, "payment.processing"
    )


async def _update_payment_from_webhook(
    intent_data: dict,
    new_status: PaymentStatus,
    sns_event_type: str,
) -> WebhookProcessResult:
    """Common logic: find record → update status → audit → publish SNS."""
    intent_id = intent_data.get("id", "")
    record = dynamodb_service.get_payment_by_intent_id(intent_id)

    if not record:
        logger.warning("No payment record found for intent %s", intent_id)
        return WebhookProcessResult(
            processed=False,
            event_type=sns_event_type,
            message=f"No record for intent {intent_id}",
        )

    previous_status = record.status.value
    dynamodb_service.update_payment_status(record.payment_id, new_status)

    cloudwatch_service.audit_payment_transition(
        payment_id=record.payment_id,
        previous_status=previous_status,
        new_status=new_status.value,
        customer_id_masked=record.customer_id_masked,
        amount=record.amount,
        currency=record.currency,
        triggered_by="webhook",
        extra={"intent_id": intent_id},
    )

    sns_service.publish_payment_event(
        event_type=sns_event_type,
        payment_id=record.payment_id,
        customer_id_masked=record.customer_id_masked,
        amount=record.amount,
        currency=record.currency,
        status=new_status.value,
    )

    return WebhookProcessResult(
        processed=True,
        event_type=sns_event_type,
        payment_id=record.payment_id,
        message=f"Status updated to {new_status.value}",
    )


# ── GET /api/payments/{payment_id} ────────────────────────────────────────────

@router.get(
    "/{payment_id}",
    response_model=PaymentStatusResponse,
    summary="Get payment status (user-scoped)",
)
async def get_payment_status(
    payment_id: str,
    user_id: str = Depends(get_current_user_id),
) -> PaymentStatusResponse:
    """
    Return the current status of a payment.
    Only returns results belonging to the authenticated user's scope.
    """
    record = dynamodb_service.get_payment_by_id(payment_id, user_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return PaymentStatusResponse(
        payment_id=record.payment_id,
        status=record.status,
        amount=record.amount,
        currency=record.currency,
        created_at=record.created_at,
        updated_at=record.updated_at,
        customer_id_masked=record.customer_id_masked,
    )


# ── GET /api/payments/dashboard ───────────────────────────────────────────────

@router.get(
    "/dashboard",
    summary="CS dashboard — all payments (masked PII)",
)
async def payments_dashboard(limit: int = 100) -> JSONResponse:
    """
    Returns all payments for the customer-service dashboard.
    All customer_id values are masked (first 4 chars + ****).
    """
    items = dynamodb_service.list_all_payments(limit=min(limit, 500))
    return JSONResponse(content={"payments": items, "count": len(items)})
