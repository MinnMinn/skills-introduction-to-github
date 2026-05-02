"""
POST /api/login — authenticates a user by email + password.

Security controls applied (see security_rules):
  Rule 1  : Passwords stored with Argon2id (t=3, m=65536, p=1).
  Rule 2  : Email lookup via ORM parameterised query.
  Rule 3  : Constant-time argon2-cffi verify().
  Rule 4  : Identical HTTP 401 body for unknown-email and wrong-password.
  Rule 5  : JWT signed with HS256; secret from env-var only.
  Rule 6  : JWT contains only sub + exp; expiry ≤ 3600 s.
  Rule 7  : JWT delivered in HttpOnly/Secure/SameSite=Strict cookie on /api.
  Rule 8  : Rate-limited: 5 email-failures/60 s + 20 IP-requests/60 s.
  Rule 9  : Password and raw JWT are never logged.
  Rule 10 : Structured audit log on every attempt.
  Rule 11 : Unexpected exceptions → generic 500 body; no stack traces.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.audit import emit_login_audit
from app.database import get_db
from app.rate_limiter import rate_limiter
from app.repositories import UserRepository
from app.schemas import LoginRequest, LoginResponse
from app.security import create_access_token, verify_password

router = APIRouter()
logger = logging.getLogger(__name__)

# Fixed error bodies — identical for all 401 cases (no user enumeration).
_INVALID_CREDENTIALS_BODY = {"error": "invalid_credentials"}
_INTERNAL_ERROR_BODY = {"error": "internal_server_error"}
_RATE_LIMITED_BODY = {"error": "too_many_requests"}


def _client_ip(request: Request) -> str:
    """Extract the most-specific client IP available."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post(
    "/api/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Validation error"},
        401: {"description": "Invalid credentials"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    summary="Authenticate a user and receive a JWT session token.",
)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Authenticate *email* + *password* and return a signed JWT on success.

    The JWT is delivered both in the JSON response body **and** in a
    Secure; HttpOnly; SameSite=Strict cookie scoped to Path=/api.
    """
    ip = _client_ip(request)
    email = body.email  # validated EmailStr — safe PII, never logged raw
    # ------------------------------------------------------------------ #
    # Rate limiting — IP first (cheapest check)
    # ------------------------------------------------------------------ #
    if rate_limiter.check_ip(ip):
        emit_login_audit(outcome="failure", email=email, source_ip=ip, http_status=429)
        return JSONResponse(status_code=429, content=_RATE_LIMITED_BODY)

    # Pre-check email failure window before hitting the database.
    if rate_limiter.is_email_limited(email):
        emit_login_audit(outcome="failure", email=email, source_ip=ip, http_status=429)
        return JSONResponse(status_code=429, content=_RATE_LIMITED_BODY)

    # ------------------------------------------------------------------ #
    # Authentication logic
    # ------------------------------------------------------------------ #
    try:
        repo = UserRepository(db)
        user = repo.get_by_email(email)

        if user is None:
            # Record a failure against this email to penalise enumeration
            # attempts, then return the generic 401 (rule 4).
            rate_limiter.check_email_failure(email)
            emit_login_audit(outcome="failure", email=email, source_ip=ip, http_status=401)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=_INVALID_CREDENTIALS_BODY,
            )

        password_ok = verify_password(body.password, user.hashed_password)

        if not password_ok:
            rate_limiter.check_email_failure(email)
            emit_login_audit(outcome="failure", email=email, source_ip=ip, http_status=401)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=_INVALID_CREDENTIALS_BODY,
            )

        # Success path
        token = create_access_token(subject=user.id)
        emit_login_audit(outcome="success", email=email, source_ip=ip, http_status=200)

        json_response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"token": token},
        )
        # Rule 7: deliver token also as a secure, HttpOnly, SameSite=Strict cookie.
        json_response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=True,
            samesite="strict",
            path="/api",
            max_age=3600,
        )
        return json_response

    except Exception:  # noqa: BLE001
        # Rule 11: log internally but never expose details to the client.
        logger.exception("Unexpected error during login — details redacted from response")
        emit_login_audit(outcome="failure", email=email, source_ip=ip, http_status=500)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_INTERNAL_ERROR_BODY,
        )
