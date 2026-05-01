"""Email service stub.

In production this would integrate with an SMTP relay / transactional email
provider (SendGrid, SES, etc.).  For now we just log the code so the flow can
be exercised without real email infrastructure.
"""

import logging

logger = logging.getLogger(__name__)


def send_verification_code(to_email: str, code: str) -> None:
    """Send (stub: log) a 6-digit verification code to *to_email*."""
    logger.info(
        "EMAIL STUB | To: %s | Subject: Your email-change verification code | Code: %s",
        to_email,
        code,
    )
