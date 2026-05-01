"""Profile email-change endpoints.

POST /api/profile/email
    Initiate an email-address change.  Sends a 6-digit code to the new address.

POST /api/profile/email/confirm
    Confirm the change by supplying the verification code.
"""
from __future__ import annotations

import hashlib
import logging
import random
import string
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.models.user import update_user_email
from app.services.email_service import send_email_verification_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile/email", tags=["profile"])

# ── Redis key helpers ──────────────────────────────────────────────────────

def _verification_key(user_id: str, new_email: str) -> str:
    """Redis key that stores the 6-digit code."""
    h = hashlib.sha256(f"{user_id}:{new_email.lower()}".encode()).hexdigest()[:16]
    return f"email_verify:{h}"


def _attempts_key(user_id: str, new_email: str) -> str:
    """Redis key that tracks failed /confirm attempts."""
    h = hashlib.sha256(f"{user_id}:{new_email.lower()}".encode()).hexdigest()[:16]
    return f"email_verify_attempts:{h}"


# ── Request / response schemas ─────────────────────────────────────────────

class EmailChangeRequest(BaseModel):
    new_email: EmailStr

    @field_validator("new_email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class EmailConfirmRequest(BaseModel):
    new_email: EmailStr
    code: str

    @field_validator("new_email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("code must be exactly 6 digits")
        return v


# ── Endpoint: initiate change ──────────────────────────────────────────────

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def request_email_change(
    body: EmailChangeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Initiate an email-address change.

    - Validates the new email format (handled by Pydantic/EmailStr → 422 if
      invalid; we convert unprocessable entity to 400 via the exception handler
      in main.py).
    - Generates a 6-digit code, stores it in Redis for 15 minutes.
    - Sends the code to the *new* email address (stubbed: logs it).
    - Returns 202 Accepted.
    """
    user_id: str = current_user["id"]
    new_email: str = body.new_email

    if new_email == current_user["email"].lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_email must differ from the current email address.",
        )

    # Generate code
    code = "".join(random.choices(string.digits, k=6))

    # Store in Redis
    redis = get_redis_client()
    vkey = _verification_key(user_id, new_email)
    redis.setex(vkey, settings.EMAIL_VERIFICATION_TTL_SECONDS, code)

    # Reset any previous attempt counter for this (user, new_email) pair
    redis.delete(_attempts_key(user_id, new_email))

    # Send (stubbed)
    send_email_verification_code(new_email, code)

    logger.info("Email change initiated for user_id=%s → %s", user_id, new_email)
    return {"detail": "Verification code sent.  Please check your new email address."}


# ── Endpoint: confirm change ───────────────────────────────────────────────

@router.post("/confirm", status_code=status.HTTP_200_OK)
def confirm_email_change(
    body: EmailConfirmRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Confirm an email-address change with the 6-digit code.

    - Validates the code against Redis.
    - Rate-limits after 5 wrong attempts (returns 401 on each wrong attempt
      and 429 once the limit is reached).
    - On success: updates the user record and clears Redis keys.
    """
    user_id: str = current_user["id"]
    new_email: str = body.new_email

    redis = get_redis_client()
    vkey = _verification_key(user_id, new_email)
    akey = _attempts_key(user_id, new_email)

    # Check if already rate-limited
    attempts = int(redis.get(akey) or 0)
    if attempts >= settings.EMAIL_CHANGE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many failed attempts.  "
                f"Please restart the email-change flow after "
                f"{settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes."
            ),
        )

    stored_code: str | None = redis.get(vkey)
    if stored_code is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verification code not found or expired.  Please restart the flow.",
        )

    if body.code != stored_code:
        # Increment attempt counter with the same TTL as the code so it
        # expires together with the verification window.
        ttl = redis.ttl(vkey)
        redis.setex(akey, max(ttl, 1), attempts + 1)

        remaining = settings.EMAIL_CHANGE_MAX_ATTEMPTS - (attempts + 1)
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many failed attempts.  "
                    f"Please restart the email-change flow after "
                    f"{settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect verification code.  {remaining} attempt(s) remaining.",
        )

    # ── Success ──────────────────────────────────────────────────────────
    update_user_email(user_id, new_email)
    redis.delete(vkey)
    redis.delete(akey)

    logger.info("Email changed successfully for user_id=%s → %s", user_id, new_email)
    return {"detail": "Email address updated successfully."}
