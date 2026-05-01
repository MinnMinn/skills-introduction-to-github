"""
DynamoDB service — payments table + idempotency-key table.

Idempotency design
------------------
Before creating a new PaymentIntent we:
  1. Attempt a conditional PutItem on the idempotency table with
     condition `attribute_not_exists(idempotency_key)`.
  2. On ConditionalCheckFailedException we read the existing record
     and return it (no new charge created).
  3. On success we proceed with the Stripe call and store the result.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.models.payment import PaymentRecord, PaymentStatus

logger = logging.getLogger(__name__)


def _get_resource():
    return boto3.resource("dynamodb", region_name="us-east-1")


def _payments_table():
    return _get_resource().Table(get_settings().DYNAMODB_PAYMENTS_TABLE)


def _idempotency_table():
    return _get_resource().Table(get_settings().DYNAMODB_IDEMPOTENCY_TABLE)


# ── Idempotency ───────────────────────────────────────────────────────────────

def claim_idempotency_key(idempotency_key: str, user_id: str) -> Optional[str]:
    """
    Atomically claim an idempotency key.

    Returns:
        None            — key is new, caller should proceed.
        str (payment_id) — key already exists, return that payment instead.
    """
    table = _idempotency_table()
    try:
        table.put_item(
            Item={
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # TTL: 24 h (set as unix timestamp)
                "ttl": int(datetime.now(timezone.utc).timestamp()) + 86400,
            },
            ConditionExpression="attribute_not_exists(idempotency_key)",
        )
        return None  # key is new
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Key already exists — find the corresponding payment
            response = table.get_item(Key={"idempotency_key": idempotency_key})
            item = response.get("Item", {})
            return item.get("payment_id")
        raise


def link_idempotency_key_to_payment(idempotency_key: str, payment_id: str) -> None:
    """Update idempotency record with the resolved payment_id."""
    table = _idempotency_table()
    table.update_item(
        Key={"idempotency_key": idempotency_key},
        UpdateExpression="SET payment_id = :pid",
        ExpressionAttributeValues={":pid": payment_id},
    )


# ── Payment records ───────────────────────────────────────────────────────────

def create_payment_record(record: PaymentRecord) -> None:
    """Persist a new payment record."""
    table = _payments_table()
    table.put_item(
        Item={
            "payment_id": record.payment_id,
            "intent_id": record.intent_id,
            "user_id": record.user_id,
            "customer_id_masked": record.customer_id_masked,
            "amount": record.amount,
            "currency": record.currency,
            "status": record.status.value,
            "idempotency_key": record.idempotency_key,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "stripe_metadata": record.stripe_metadata,
        }
    )
    logger.info("Payment record created: payment_id=%s", record.payment_id)


def get_payment_by_id(payment_id: str, user_id: str) -> Optional[PaymentRecord]:
    """
    Fetch a payment record scoped to a specific user.
    Returns None if not found or belongs to a different user.
    """
    table = _payments_table()
    response = table.get_item(Key={"payment_id": payment_id})
    item = response.get("Item")
    if not item:
        return None
    if item.get("user_id") != user_id:
        return None  # silently scope — don't leak existence
    return _item_to_record(item)


def get_payment_by_intent_id(intent_id: str) -> Optional[PaymentRecord]:
    """Find a payment by Stripe intent_id (used during webhook processing)."""
    table = _payments_table()
    # intent_id is a GSI in the actual table definition (see CDK stack)
    response = table.query(
        IndexName="intent_id-index",
        KeyConditionExpression=Key("intent_id").eq(intent_id),
        Limit=1,
    )
    items = response.get("Items", [])
    return _item_to_record(items[0]) if items else None


def update_payment_status(payment_id: str, new_status: PaymentStatus) -> None:
    """Update the status of an existing payment record."""
    table = _payments_table()
    table.update_item(
        Key={"payment_id": payment_id},
        UpdateExpression="SET #s = :status, updated_at = :ua",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": new_status.value,
            ":ua": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("Payment %s status → %s", payment_id, new_status.value)


def list_all_payments(limit: int = 100) -> list[dict]:
    """
    Scan all payments for the CS dashboard.
    Returns masked records — no raw PII.
    """
    table = _payments_table()
    response = table.scan(Limit=limit)
    return response.get("Items", [])


# ── Internal helpers ──────────────────────────────────────────────────────────

def _item_to_record(item: dict) -> PaymentRecord:
    return PaymentRecord(
        payment_id=item["payment_id"],
        intent_id=item["intent_id"],
        user_id=item["user_id"],
        customer_id_masked=item["customer_id_masked"],
        amount=int(item["amount"]),
        currency=item["currency"],
        status=PaymentStatus(item["status"]),
        idempotency_key=item["idempotency_key"],
        created_at=datetime.fromisoformat(item["created_at"]),
        updated_at=datetime.fromisoformat(item["updated_at"]),
        stripe_metadata=item.get("stripe_metadata", {}),
    )
