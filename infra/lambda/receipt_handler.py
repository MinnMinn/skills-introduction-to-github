"""
Lambda function: Payment Receipt Handler

Triggered by SNS payment events. Writes a JSON receipt to S3.

Event types handled:
  - payment.succeeded  → generates and stores a receipt
  - payment.failed     → logs the failure audit record
  - payment.created    → logs the creation record

PCI controls:
  - No raw card data in any event payload (enforced upstream).
  - customer_id is always masked before reaching this function.
  - No PII written to CloudWatch (structured log with masked fields only).
"""
import json
import logging
import os
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RECEIPTS_BUCKET = os.environ.get("RECEIPTS_BUCKET", "")
CLOUDWATCH_LOG_GROUP = os.environ.get("CLOUDWATCH_LOG_GROUP", "/payments/audit")

_s3 = boto3.client("s3")
_logs = boto3.client("logs")


def handler(event: dict, context) -> dict:
    """
    Lambda handler — processes SNS records.

    Each SNS record contains a JSON payment event.
    """
    processed = 0
    failed = 0

    for record in event.get("Records", []):
        try:
            sns_message = record["Sns"]["Message"]
            payment_event = json.loads(sns_message)
            _process_payment_event(payment_event)
            processed += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to process SNS record: %s", exc)
            failed += 1

    logger.info("Processed %d records, %d failed", processed, failed)
    return {"processed": processed, "failed": failed}


def _process_payment_event(event: dict) -> None:
    """Route event to the appropriate handler."""
    event_type = event.get("event_type", "")
    payment_id = event.get("payment_id", "unknown")

    logger.info("Processing event: %s payment_id=%s", event_type, payment_id)

    if event_type == "payment.succeeded":
        _write_receipt(event)
    elif event_type in ("payment.failed", "payment.canceled"):
        _write_failure_record(event)

    # Always write an audit entry
    _write_audit_log(event)


def _write_receipt(event: dict) -> None:
    """Write a payment receipt JSON to S3."""
    if not RECEIPTS_BUCKET:
        logger.warning("RECEIPTS_BUCKET not configured — skipping S3 write")
        return

    payment_id = event["payment_id"]
    timestamp = datetime.now(timezone.utc).isoformat()
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")

    receipt = {
        "receipt_type": "payment_confirmation",
        "payment_id": payment_id,
        "amount": event.get("amount"),
        "currency": event.get("currency"),
        "status": event.get("status"),
        # Masked — never store real customer_id in receipts
        "customer_ref": event.get("customer_id_masked"),
        "generated_at": timestamp,
    }

    key = f"receipts/{date_prefix}/{payment_id}.json"
    try:
        _s3.put_object(
            Bucket=RECEIPTS_BUCKET,
            Key=key,
            Body=json.dumps(receipt, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
        logger.info("Receipt written: s3://%s/%s", RECEIPTS_BUCKET, key)
    except ClientError as exc:
        logger.error("Failed to write receipt to S3: %s", exc)
        raise


def _write_failure_record(event: dict) -> None:
    """Write a failure audit record to S3 for ops visibility."""
    if not RECEIPTS_BUCKET:
        return

    payment_id = event["payment_id"]
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    key = f"failures/{date_prefix}/{payment_id}.json"

    record = {
        "event_type": event.get("event_type"),
        "payment_id": payment_id,
        "amount": event.get("amount"),
        "currency": event.get("currency"),
        "customer_ref": event.get("customer_id_masked"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        _s3.put_object(
            Bucket=RECEIPTS_BUCKET,
            Key=key,
            Body=json.dumps(record, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )
    except ClientError as exc:
        logger.error("Failed to write failure record: %s", exc)


def _write_audit_log(event: dict) -> None:
    """Append a structured audit entry to the CloudWatch log group."""
    stream_name = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    _ensure_log_stream(CLOUDWATCH_LOG_GROUP, stream_name)

    log_entry = {
        "source": "receipt-lambda",
        "event_type": event.get("event_type"),
        "payment_id": event.get("payment_id"),
        "status": event.get("status"),
        "customer_ref": event.get("customer_id_masked"),  # masked
        "timestamp": event.get("timestamp"),
    }

    try:
        _logs.put_log_events(
            logGroupName=CLOUDWATCH_LOG_GROUP,
            logStreamName=stream_name,
            logEvents=[{
                "timestamp": int(time.time() * 1000),
                "message": json.dumps(log_entry),
            }],
        )
    except ClientError as exc:
        # Non-fatal — audit failure must not prevent receipt generation
        logger.error("CloudWatch audit log write failed: %s", exc)


_stream_cache: set[str] = set()


def _ensure_log_stream(log_group: str, stream_name: str) -> None:
    if stream_name in _stream_cache:
        return
    try:
        _logs.create_log_stream(
            logGroupName=log_group, logStreamName=stream_name
        )
        _stream_cache.add(stream_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            _stream_cache.add(stream_name)
        else:
            raise
