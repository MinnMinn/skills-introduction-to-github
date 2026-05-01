"""
Profile management endpoints.

POST /api/profile/email
    Initiate an email-change request.
    Requires a valid JWT (Bearer token).
    Validates the new email, generates a 6-digit code, stores it in Redis
    with a 15-minute TTL, stubs an email send (logs the code), and returns
    202 Accepted.

POST /api/profile/email/confirm
    Confirm an email change by supplying the verification code.
    Requires a valid JWT.
    Validates the code against Redis, enforces a 5-attempt rate limit,
    updates the users table, and returns 200 OK.
"""
from __future__ import annotations

import hashlib
import logging
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status

import app.audit as audit
import app.redis_client as redis_client
import app.rate_limiter as rate_limiter
from app.auth import get_current_user_id
from app.config import VERIFICATION_CODE_TTL_SECONDS
from app.email_service import send_verification_code
from app.models import EmailChangeRequest, EmailConfirmRequest, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REDIS_KEY_PREFIX = "email_verify:"


def _verification_key(user_id: str, new_email: str) -> str:
    """
    Build a Redis key that encodes both the user and the target email.
    We hash the email to avoid storing PII as a plain key name.
    """
    email_hash = hashlib.sha256(new_email.lower().encode()).hexdigest()[:16]
    return f"{_REDIS_KEY_PREFIX}{user_id}:{email_hash}"


def _generate_code() -> str:
    """Return a cryptographically-adequate 6-digit code."""
    # secrets.randbelow is safer, but random.SystemRandom uses os.urandom
    # which is sufficient for short-lived verification codes.
    rng = random.SystemRandom()
    return "".join(rng.choices(string.digits, k=6))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/email",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Request an email-address change",
)
def request_email_change(
    body: EmailChangeRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    """
    Initiate an email change for the authenticated user.

    - **new_email**: The desired new email address (validated server-side).

    Returns **202 Accepted** and sends a 6-digit code to the new address.
    The code expires after 15 minutes.
    """
    new_email: str = str(body.new_email).lower()

    # Generate and store the verification code in Redis.
    code = _generate_code()
    r = redis_client.get_redis()
    key = _verification_key(user_id, new_email)
    r.setex(key, VERIFICATION_CODE_TTL_SECONDS, code)

    # Stub the email send (log only — no real SMTP call).
    send_verification_code(to_email=new_email, code=code)

    logger.info("Email-change initiated for user_id=%s → %s", user_id, new_email)
    return MessageResponse(
        message="Verification code sent. Please check your new email address."
    )


@router.post(
    "/email/confirm",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Confirm an email-address change",
)
def confirm_email_change(
    body: EmailConfirmRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    """
    Confirm the email change by supplying the 6-digit code.

    - **new_email**: Must match the address supplied in the initiation request.
    - **code**: The 6-digit code delivered to the new address.

    Returns **200 OK** on success.  After 5 wrong attempts the request is
    rate-limited and returns **401**.
    """
    new_email: str = str(body.new_email).lower()
    r = redis_client.get_redis()

    # Rate-limit check *before* validating the code to prevent enumeration.
    if rate_limiter.is_rate_limited(r, user_id, new_email):
        logger.warning(
            "Rate limit exceeded for user_id=%s on email confirm", user_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many failed attempts. Please request a new verification code.",
        )

    # Look up the pending code.
    key = _verification_key(user_id, new_email)
    stored_code: str | None = r.get(key)

    if stored_code is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No pending email-change request found, or code has expired.",
        )

    # Constant-time comparison to prevent timing attacks.
    import hmac as _hmac

    if not _hmac.compare_digest(stored_code, body.code):
        attempts = rate_limiter.increment_attempt(r, user_id, new_email)
        remaining = max(0, 5 - attempts)
        logger.warning(
            "Wrong verification code for user_id=%s (%d attempt(s), %d remaining)",
            user_id,
            attempts,
            remaining,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    # Success — update the user record and clean up Redis.
    audit.update_user_email(user_id, new_email)
    r.delete(key)
    rate_limiter.reset_attempts(r, user_id, new_email)

    logger.info("Email changed successfully for user_id=%s → %s", user_id, new_email)
    return MessageResponse(message="Email address updated successfully.")
