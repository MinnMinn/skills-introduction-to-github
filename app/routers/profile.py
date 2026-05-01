"""
Profile router — email-change flow.

Endpoints
---------
POST /api/profile/email
    • Requires JWT Bearer token.
    • Validates new_email format (handled by Pydantic EmailStr).
    • Generates a 6-digit code, stores in Redis (15-min TTL).
    • Stubs an email send (logs the code).
    • Returns 202 Accepted.

POST /api/profile/email/confirm
    • Requires JWT Bearer token.
    • Validates the code against the Redis store.
    • On success: updates the users table, old email valid for 30 days.
    • On wrong code: 401; after 5 wrong attempts: 429 Too Many Requests.
"""
from __future__ import annotations

import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_redis
from app.models import EmailChangeRequest, EmailConfirmRequest, MessageResponse
from app.services import email_service, verification
from app import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ---------------------------------------------------------------------------
# POST /api/profile/email
# ---------------------------------------------------------------------------

@router.post(
    "/email",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    responses={
        400: {"description": "Malformed email address"},
        401: {"description": "Unauthorized — missing or invalid JWT"},
    },
    summary="Request an email-change verification code",
)
def request_email_change(
    body: EmailChangeRequest,
    current_user: dict = Depends(get_current_user),
    r: redis_lib.Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Initiates an email-change flow.

    Generates a 6-digit code, stores it in Redis with a 15-minute TTL, and
    (stub) emails it to *new_email*.  The caller must subsequently POST to
    ``/api/profile/email/confirm`` with the same new_email and the code.

    **Pydantic's ``EmailStr`` field already rejects malformed addresses with
    a 422 Unprocessable Entity; this endpoint layer returns 400 explicitly
    when we detect a business-rule violation.**
    """
    new_email: str = str(body.new_email).lower()
    user_id: str = current_user["id"]

    # Prevent changing to the same email (not strictly required but sensible)
    if new_email == current_user["email"].lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email must differ from the current email.",
        )

    code = verification.generate_and_store_code(r, user_id, new_email)
    email_service.send_verification_code(new_email, code)

    logger.info("Email-change initiated for user=%s", user_id)
    return MessageResponse(
        message="Verification code sent. Please check your new email inbox."
    )


# ---------------------------------------------------------------------------
# POST /api/profile/email/confirm
# ---------------------------------------------------------------------------

@router.post(
    "/email/confirm",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    responses={
        401: {"description": "Unauthorized — bad JWT or wrong verification code"},
        429: {"description": "Too many incorrect attempts"},
    },
    summary="Confirm the email-change verification code",
)
def confirm_email_change(
    body: EmailConfirmRequest,
    current_user: dict = Depends(get_current_user),
    r: redis_lib.Redis = Depends(get_redis),
) -> MessageResponse:
    """
    Completes the email-change flow.

    Validates the 6-digit *code* against the value stored in Redis for the
    authenticated user + *new_email* pair.

    * Wrong code → 401 (up to 5 attempts).
    * After 5 wrong attempts → 429 Too Many Requests.
    * On success → updates the user record; old email remains valid for 30 days.
    """
    new_email: str = str(body.new_email).lower()
    user_id: str = current_user["id"]

    is_valid, is_rate_limited = verification.verify_code(
        r, user_id, new_email, body.code
    )

    if is_rate_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many incorrect verification attempts. "
                "Please request a new code."
            ),
        )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    updated_user = database.update_user_email(user_id, new_email)
    if updated_user is None:
        # Shouldn't happen — user was validated by JWT dependency
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error updating user record.",
        )

    logger.info(
        "Email changed for user=%s. Old email valid for 30 days (audit trail).",
        user_id,
    )
    return MessageResponse(message="Email address updated successfully.")
