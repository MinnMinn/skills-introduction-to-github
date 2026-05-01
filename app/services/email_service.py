"""
Email service — **stubbed** for now.

In production replace ``send_verification_code`` with a real SMTP / SES call.
We log the code so it is visible in local development and test runs without
any external dependency.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_verification_code(to_email: str, code: str) -> None:
    """
    Send (or stub) a verification email containing *code* to *to_email*.

    Currently just logs the code.  Replace the body of this function with a
    real email-sending implementation (e.g. smtplib, boto3 SES, SendGrid SDK).
    """
    logger.info(
        "EMAIL STUB — To: %s | Subject: Your email-change verification code"
        " | Body: Your code is %s (valid for 15 minutes).",
        to_email,
        code,
    )
