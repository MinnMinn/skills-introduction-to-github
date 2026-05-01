"""
Email sending stub.

In production, replace the body of ``send_verification_code`` with a real
email provider call (SES, SendGrid, etc.).  For now, the code is only logged
so that no credentials are required in development or CI.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def send_verification_code(to_email: str, code: str) -> None:
    """
    Stub: log the 6-digit verification code instead of sending a real email.

    Replace this implementation with a real email provider integration.
    The ``code`` must never be returned to the HTTP response — only delivered
    out-of-band.
    """
    # SECURITY: In production, strip the code from logs or use a structured
    # logging system that redacts PII fields.
    logger.info(
        "EMAIL STUB — verification code for %s: %s",
        to_email,
        code,
    )
