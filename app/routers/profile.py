"""
Profile endpoints — email change flow.

POST /api/profile/email
    Initiates the email-change flow.  Requires a valid Bearer JWT.
    Generates a 6-digit code, stores it in Redis (15-min TTL), stubs an email send,
    and returns 202 Accepted.

POST /api/profile/email/confirm
    Confirms the code.  On success, updates the user's email and returns 200.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.email_utils import send_verification_email
from app.models import EmailChangeRequest, EmailConfirmRequest, MessageResponse
from app.redis_client import (
    CodeNotFound,
    InvalidCode,
    RateLimitExceeded,
    generate_code,
    store_verification_code,
    verify_code,
)
from app import db

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post(
    "/email",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
    summary="Initiate email address change",
)
async def initiate_email_change(
    body: EmailChangeRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """
    Start the email-change verification flow.

    - Validates the new email format (handled by Pydantic EmailStr → 422 / 400).
    - Generates a 6-digit code and stores it in Redis with a 15-minute TTL.
    - Stubs an email send (logs to stdout).
    - Returns 202 Accepted.
    """
    new_email = str(body.new_email).lower()

    # Reject if new email is the same as the current one
    if new_email == current_user["email"].lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email must differ from your current email address.",
        )

    code = generate_code()
    store_verification_code(current_user["id"], new_email, code)
    send_verification_email(new_email, code)

    return MessageResponse(
        message="A verification code has been sent to the new email address. "
                "It is valid for 15 minutes."
    )


@router.post(
    "/email/confirm",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Confirm email address change with verification code",
)
async def confirm_email_change(
    body: EmailConfirmRequest,
    current_user: dict = Depends(get_current_user),
) -> MessageResponse:
    """
    Confirm the email-change verification code.

    - Verifies the 6-digit code against the Redis-stored value.
    - Rate-limits to 5 failed attempts; returns 401 thereafter.
    - On success, updates the user's primary email (old email remains valid for 30 days).
    - Returns 200 OK on success.
    """
    new_email = str(body.new_email).lower()

    try:
        verify_code(current_user["id"], new_email, body.code)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except InvalidCode as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except CodeNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    updated_user = db.update_user_email(current_user["id"], new_email)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user email.",
        )

    return MessageResponse(message="Email address updated successfully.")
