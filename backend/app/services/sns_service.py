"""
SNS publisher for payment events.

Publishes structured payment events to the SNS topic.
The Lambda consumer (infra/lambda/receipt_handler.py) subscribes
and writes receipt documents to S3.
"""
import json
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _sns_client():
    return boto3.client("sns", region_name="us-east-1")


def publish_payment_event(
    event_type: str,
    payment_id: str,
    customer_id_masked: str,
    amount: int,
    currency: str,
    status: str,
    extra: dict | None = None,
) -> None:
    """
    Publish a payment domain event to the SNS topic.

    The message contains no raw PII.  customer_id must already be masked.
    """
    settings = get_settings()
    topic_arn = settings.SNS_PAYMENT_EVENTS_TOPIC_ARN
    if not topic_arn:
        logger.warning("SNS_PAYMENT_EVENTS_TOPIC_ARN not configured — skipping publish")
        return

    message = {
        "event_type": event_type,
        "payment_id": payment_id,
        "customer_id_masked": customer_id_masked,
        "amount": amount,
        "currency": currency,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }

    try:
        _sns_client().publish(
            TopicArn=topic_arn,
            Message=json.dumps(message),
            Subject=event_type,
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": event_type,
                }
            },
        )
        logger.info("Published SNS event: %s for payment %s", event_type, payment_id)
    except ClientError as exc:
        logger.error("Failed to publish SNS event: %s", exc)
        # Non-fatal — SNS failure must not block the API response
