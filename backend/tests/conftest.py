"""
Shared pytest fixtures for the payments backend tests.
"""
import os
import time
import uuid

import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient

# ── Set testing env vars BEFORE importing app modules ────────────────────────
os.environ.update({
    "APP_ENV": "testing",
    "STRIPE_SECRET_KEY": "sk_test_fake_key",
    "STRIPE_WEBHOOK_SECRET": "whsec_test_fake_secret",
    "DYNAMODB_PAYMENTS_TABLE": "payments_test",
    "DYNAMODB_IDEMPOTENCY_TABLE": "idempotency_test",
    "SNS_PAYMENT_EVENTS_TOPIC_ARN": "",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SECURITY_TOKEN": "testing",
    "AWS_SESSION_TOKEN": "testing",
})

from app.core.config import get_settings
get_settings.cache_clear()  # ensure fresh settings after env override


@pytest.fixture(scope="function")
def aws_credentials():
    """Ensure moto uses fake credentials."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def dynamodb_tables(aws_credentials):
    """Create DynamoDB tables in moto."""
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")

        # Payments table with GSI on intent_id
        ddb.create_table(
            TableName="payments_test",
            KeySchema=[{"AttributeName": "payment_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "payment_id", "AttributeType": "S"},
                {"AttributeName": "intent_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "intent_id-index",
                "KeySchema": [{"AttributeName": "intent_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            }],
            BillingMode="PAY_PER_REQUEST",
        )

        # Idempotency table
        ddb.create_table(
            TableName="idempotency_test",
            KeySchema=[{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "idempotency_key", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield ddb


@pytest.fixture(scope="function")
def test_client(dynamodb_tables):
    """FastAPI test client with mocked AWS inside moto context."""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def valid_create_intent_payload():
    return {
        "amount": 1000,
        "currency": "USD",
        "customer_id": "cust_abc123",
        "idempotency_key": str(uuid.uuid4()),
        "payment_method_id": "pm_test_fake",
        "metadata": {},
    }


@pytest.fixture
def user_headers():
    return {"X-User-ID": "user_test_001"}
