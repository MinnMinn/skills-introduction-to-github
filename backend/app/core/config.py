"""
Application configuration loaded from environment variables.
Secrets (Stripe keys) are pulled from AWS Secrets Manager at startup
when running in a cloud environment.
"""
import json
import logging
import os
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


def _fetch_secret(secret_name: str) -> dict:
    """Retrieve a JSON secret from AWS Secrets Manager."""
    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Could not fetch secret %s: %s", secret_name, exc)
        return {}


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Stripe ───────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # AWS Secrets Manager secret name that holds
    # {"STRIPE_SECRET_KEY": "...", "STRIPE_WEBHOOK_SECRET": "..."}
    AWS_STRIPE_SECRET_NAME: str = "stripe/credentials"

    # ── DynamoDB ─────────────────────────────────────────────────────
    DYNAMODB_PAYMENTS_TABLE: str = "payments"
    DYNAMODB_IDEMPOTENCY_TABLE: str = "payment_idempotency_keys"

    # ── SNS ──────────────────────────────────────────────────────────
    SNS_PAYMENT_EVENTS_TOPIC_ARN: str = ""

    # ── CloudWatch ───────────────────────────────────────────────────
    CLOUDWATCH_LOG_GROUP: str = "/payments/audit"

    # ── Rate limiting ────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True

    def load_aws_secrets(self) -> None:
        """Populate Stripe credentials from Secrets Manager if not set via env."""
        if self.STRIPE_SECRET_KEY and self.STRIPE_WEBHOOK_SECRET:
            return  # already set (e.g. via env in tests)
        secrets = _fetch_secret(self.AWS_STRIPE_SECRET_NAME)
        if secrets.get("STRIPE_SECRET_KEY"):
            self.STRIPE_SECRET_KEY = secrets["STRIPE_SECRET_KEY"]
        if secrets.get("STRIPE_WEBHOOK_SECRET"):
            self.STRIPE_WEBHOOK_SECRET = secrets["STRIPE_WEBHOOK_SECRET"]


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if settings.APP_ENV != "testing":
        settings.load_aws_secrets()
    return settings
