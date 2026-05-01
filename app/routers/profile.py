"""Profile-related endpoints.

POST /api/profile/email         — initiate an email-change request
POST /api/profile/email/confirm — confirm the change with a 6-digit code
"""

import logging
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user_id
from app.config import settings
from app.db import get_user, update_user_email
from app.email_service import send_verification_code
from app.models import EmailChangeRequest, EmailConfirmRequest, MessageResponse
from app.redis_client import (
    delete_verification_keys,
    get_attempts,
    get_verification_code,
    increment_attempts,
    store_verification_code,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _generate_code(length: int = 6) -> str:
    """Return a random *length*-digit numeric string."""
    return "".join(random.choices(string.digits, k=length))


# ── POST /api/profile/email ──────────────────────────────────────────────────

@router.post(
    "/email",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Initiate an email-address change",
)
def request_email_change(
    body: EmailChangeRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    """Send a 6-digit verification code to *new_email*.

    The code is stored in Redis with a 15-minute TTL keyed by
    ``email_change:{user_id}:{sha256(new_email)}``.

    Possible responses:
    - **202** — code sent (or logged, in the stub implementation)
    - **400** — *new_email* is not a valid e-mail address (handled by Pydantic)
    - **401** — missing or invalid JWT
    """
    # Ensure the user actually exists in our system
    user = get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_email = str(body.new_email).lower()

    # Prevent a user from "changing" to their current address
    if new_email == user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email must differ from the current email",
        )

    code = _generate_code()
    store_verification_code(user_id, new_email, code)
    send_verification_code(new_email, code)

    logger.info("Email-change initiated: user=%s new_email=%s", user_id, new_email)
    return MessageResponse(detail="Verification code sent. Please check your new inbox.")


# ── POST /api/profile/email/confirm ──────────────────────────────────────────

@router.post(
    "/email/confirm",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Confirm an email-address change with the verification code",
)
def confirm_email_change(
    body: EmailConfirmRequest,
    user_id: str = Depends(get_current_user_id),
) -> MessageResponse:
    """Verify the 6-digit code and update the user's email address.

    Possible responses:
    - **200** — email updated successfully
    - **400** — *new_email* is not a valid e-mail address (handled by Pydantic)
    - **401** — missing or invalid JWT, wrong code, or rate-limited (≥ 5 wrong attempts)
    - **404** — no pending code found for this email (expired or never initiated)
    """
    new_email = str(body.new_email).lower()

    # ── Rate-limit check ──────────────────────────────────────────────────────
    attempts = get_attempts(user_id, new_email)
    if attempts >= settings.max_verify_attempts:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Too many failed attempts. Please request a new verification code."
            ),
        )

    # ── Code lookup ───────────────────────────────────────────────────────────
    stored_code = get_verification_code(user_id, new_email)
    if stored_code is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending email-change request found. Please initiate a new request.",
        )

    # ── Code validation ───────────────────────────────────────────────────────
    if body.code != stored_code:
        new_attempts = increment_attempts(user_id, new_email)
        remaining = max(0, settings.max_verify_attempts - new_attempts)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Invalid verification code. "
                f"{remaining} attempt(s) remaining before you are locked out."
            ),
        )

    # ── Apply the email change ────────────────────────────────────────────────
    success = update_user_email(user_id, new_email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    delete_verification_keys(user_id, new_email)
    logger.info("Email changed successfully: user=%s new_email=%s", user_id, new_email)
    return MessageResponse(detail="Email address updated successfully.")
