"""Stubbed email service.

In production this would integrate with SendGrid / SES / etc.
For now every send is logged to stdout so behaviour is observable in tests
and local development without any external dependencies.
"""
import logging

logger = logging.getLogger(__name__)


def send_email_verification_code(to_email: str, code: str) -> None:
    """Send (stub) a 6-digit verification code to *to_email*.

    Logs the code at INFO level.  Replace with a real transport when ready.
    """
    logger.info(
        "EMAIL STUB | To: %s | Subject: Confirm your email change | Code: %s",
        to_email,
        code,
    )
