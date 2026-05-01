"""
CloudWatch audit-log service.

Every payment state transition is written as a structured log event to a
dedicated CloudWatch log group (/payments/audit).  No PII is emitted —
customer_id is always masked before reaching this service.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level sequence token cache (single-instance; use Redis in multi-pod)
_sequence_tokens: dict[str, Optional[str]] = {}


def _cw_client():
    return boto3.client("logs", region_name="us-east-1")


def _ensure_log_stream(log_group: str, stream_name: str) -> None:
    client = _cw_client()
    try:
        client.create_log_stream(logGroupName=log_group, logStreamName=stream_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceAlreadyExistsException":
            raise


def audit_payment_transition(
    payment_id: str,
    previous_status: str,
    new_status: str,
    customer_id_masked: str,
    amount: int,
    currency: str,
    triggered_by: str = "system",
    extra: Optional[dict] = None,
) -> None:
    """
    Write a structured audit log entry for a payment state transition.

    Args:
        payment_id:           Internal payment UUID.
        previous_status:      Status before transition.
        new_status:           Status after transition.
        customer_id_masked:   Already-masked customer ID (first 4 chars + ****).
        amount:               Payment amount in smallest unit.
        currency:             ISO-4217 currency code.
        triggered_by:         'user', 'webhook', 'system', etc.
        extra:                Additional structured fields (no PAN/PII).
    """
    settings = get_settings()
    log_group = settings.CLOUDWATCH_LOG_GROUP
    stream_name = datetime.now(timezone.utc).strftime("%Y/%m/%d")

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "payment.status_transition",
        "payment_id": payment_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "customer_id_masked": customer_id_masked,
        "amount": amount,
        "currency": currency,
        "triggered_by": triggered_by,
        **(extra or {}),
    }

    _put_log_event(log_group, stream_name, json.dumps(event))


def _put_log_event(log_group: str, stream_name: str, message: str) -> None:
    """Internal helper — writes one log event; handles sequence tokens."""
    client = _cw_client()
    _ensure_log_stream(log_group, stream_name)

    kwargs: dict = {
        "logGroupName": log_group,
        "logStreamName": stream_name,
        "logEvents": [{"timestamp": int(time.time() * 1000), "message": message}],
    }
    token = _sequence_tokens.get(stream_name)
    if token:
        kwargs["sequenceToken"] = token

    try:
        response = client.put_log_events(**kwargs)
        _sequence_tokens[stream_name] = response.get("nextSequenceToken")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("InvalidSequenceTokenException", "DataAlreadyAcceptedException"):
            # Recover: use the correct token from the exception message
            correct_token = exc.response["Error"].get("expectedSequenceToken")
            if correct_token:
                _sequence_tokens[stream_name] = correct_token
                kwargs["sequenceToken"] = correct_token
                response = client.put_log_events(**kwargs)
                _sequence_tokens[stream_name] = response.get("nextSequenceToken")
        else:
            logger.error("Failed to write CloudWatch audit log: %s", exc)
            # Non-fatal — audit failure must not break the payment flow
