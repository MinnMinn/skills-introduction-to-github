"""
Email utilities — stubbed for now.

Replace `send_verification_email` with a real SMTP / SES call in production.
The stub logs the code so that local development and tests can inspect it.
"""
import logging

logger = logging.getLogger(__name__)


def send_verification_email(to_address: str, code: str) -> None:
    """
    Send the 6-digit verification *code* to *to_address*.

    STUB: logs the code instead of sending a real email.
    In production wire this up to an email provider (SES, SendGrid, …).
    """
    logger.info(
        "EMAIL STUB — To: %s | Subject: Your email change verification code | "
        "Body: Your verification code is %s (valid for 15 minutes). "
        "If you did not request this change, ignore this message.",
        to_address,
        code,
    )
