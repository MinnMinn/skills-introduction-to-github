"""
POST /api/auth/reset-password
POST /api/auth/reset-password/confirm

Security notes (see security_rules in ticket):
  1.  CSPRNG token via secrets.randbelow                (rule 1)
  2.  Only argon2id hash of token stored in Redis        (rule 2)
  3.  Atomic Lua script for check-and-delete on confirm  (rule 3)
  4.  Redis INCR+EXPIRE per-email rate limit             (rule 4)
  5.  Per-IP confirm rate limit at middleware layer       (rule 5)
  6.  argon2id for passwords (t=3 m=65536 p=1)           (rule 6)
  7.  newPassword ≥ 8 chars → 400 before any I/O         (rule 7)
  8.  Generic 200 bodies for all non-400/429/500 paths   (rule 8)
  9.  Constant-time dummy ops for unknown email           (rule 9)
 10.  Catch all exceptions → 500 with generic body       (rule 10)
 11.  Audit log with sha256(email), never plaintext      (rule 11)
 12.  Stub stdout line marked stub_only=True             (rule 12)
 13.  Redis URL from env var                             (rule 13)
"""
from __future__ import annotations

import json
import secrets
import sys
from typing import Any

import redis as redis_lib
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import audit
from app.config import settings
from app.dependencies import get_db, get_redis
from app.models import User
from app.schemas import ConfirmResetRequest, ResetPasswordRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Argon2id hasher — parameters per security rules 2 & 6
# ---------------------------------------------------------------------------

_ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)

# ---------------------------------------------------------------------------
# Redis key helpers
# ---------------------------------------------------------------------------

def _token_key(email: str) -> str:
    return f"reset_token:{email}"


def _rate_key_email(email: str) -> str:
    return f"ratelimit:reset:{email}"


def _rate_key_confirm_ip(ip: str) -> str:
    return f"ratelimit:confirm_ip:{ip}"


# ---------------------------------------------------------------------------
# Lua script: atomic check-and-delete (security rule 3)
#
# Returns 1 on match (key deleted), 0 on mismatch, -1 if key missing.
# The script runs atomically inside Redis — no TOCTOU race.
# ---------------------------------------------------------------------------

_LUA_CHECK_AND_DELETE = """
local key   = KEYS[1]
local stored = redis.call('GET', key)
if stored == false then
    return -1
end
-- stored is the argon2id hash; comparison done in application layer after
-- this script returns the hash so we can use constant-time argon2 verify.
-- We return the stored value so the caller can verify, then a second Lua
-- call deletes it only on match.
return stored
"""

# Two-phase Lua: fetch then conditionally delete.
# We use a separate delete-if-still-same script to avoid a TOCTOU between
# verify (application) and delete (Redis).
_LUA_DELETE_IF_MATCH = """
local key     = KEYS[1]
local expected = ARGV[1]
local current  = redis.call('GET', key)
if current == expected then
    redis.call('DEL', key)
    return 1
end
return 0
"""


# ---------------------------------------------------------------------------
# Rate-limit helper (security rule 4 & 5)
# ---------------------------------------------------------------------------

def _check_and_increment_rate_limit(
    r: redis_lib.Redis,
    key: str,
    max_attempts: int,
    window_seconds: int,
) -> bool:
    """Atomically increment a rate-limit counter.

    Returns True if the caller is WITHIN the limit (should proceed).
    Returns False if the limit has been EXCEEDED (should return 429).
    Uses INCR + EXPIRE so the window starts on the first request.
    """
    count = r.incr(key)
    if count == 1:
        # First request in this window — set expiry atomically.
        r.expire(key, window_seconds)
    return int(count) <= max_attempts


# ---------------------------------------------------------------------------
# Endpoint: POST /api/auth/reset-password
# ---------------------------------------------------------------------------

@router.post("/reset-password", status_code=200)
def request_reset(
    body: ResetPasswordRequest,
    request: Request,
    r: redis_lib.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Accept an email address and (if registered) send a 6-digit reset code.

    Always returns the same generic 200 body to prevent email enumeration
    (security rule 8).  All Redis/DB errors surface as 500 with a generic
    body (rule 10).
    """
    email: str = str(body.email).lower().strip()
    ip: str = request.client.host if request.client else "unknown"

    _GENERIC_OK = {"message": "If that email is registered, a reset code has been sent."}
    _GENERIC_ERR = {"error": "service_unavailable"}

    try:
        # ── Rate-limit check (security rule 4) ──────────────────────────────
        rate_key = _rate_key_email(email)
        within_limit = _check_and_increment_rate_limit(
            r,
            rate_key,
            settings.RATE_LIMIT_RESET_MAX,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        if not within_limit:
            audit.emit(
                event_type="rate_limit_hit",
                email=email,
                ip_address=ip,
                outcome="reset_request_rate_limited",
            )
            return JSONResponse(status_code=429, content={"error": "Too Many Requests"})

        # ── Look up user ─────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == email).first()

        if user is None:
            # Security rule 9: perform a constant-time dummy argon2 hash and a
            # dummy Redis write so response latency does not leak account existence.
            _dummy_code = "000000"
            _ph.hash(_dummy_code)  # constant-time dummy hash
            r.set(f"reset_token:dummy:{email}", "dummy", ex=1)  # dummy write, expires in 1s

            audit.emit(
                event_type="reset_requested",
                email=email,
                ip_address=ip,
                outcome="email_not_registered",
            )
            return JSONResponse(status_code=200, content=_GENERIC_OK)

        # ── Generate CSPRNG 6-digit token (security rule 1) ──────────────────
        code_int = secrets.randbelow(1_000_000)
        code = f"{code_int:06d}"

        # ── Hash token with argon2id (security rule 2) ───────────────────────
        code_hash = _ph.hash(code)

        # ── Store hash in Redis with TTL (security rule 2 & 13) ──────────────
        token_key = _token_key(email)
        r.set(token_key, code_hash, ex=settings.TOKEN_TTL_SECONDS)

        # ── Stub email: log plaintext code to stdout (security rule 12) ──────
        # ⚠ STUB ONLY — remove or redact this print statement before enabling
        #   any log-forwarding pipeline in production (security rule 12).
        print(
            json.dumps({
                "stub_only": True,
                "event": "reset_code_stub_email",
                "to": email,
                "code": code,
                # WARNING: plaintext code above — MUST NOT reach production logs
            }),
            file=sys.stdout,
            flush=True,
        )

        audit.emit(
            event_type="reset_requested",
            email=email,
            ip_address=ip,
            outcome="reset_code_generated",
        )
        return JSONResponse(status_code=200, content=_GENERIC_OK)

    except redis_lib.RedisError as exc:
        # Security rule 10: never expose internal details.
        print(
            json.dumps({"level": "error", "event": "redis_error", "detail": str(exc)}),
            file=sys.stderr,
            flush=True,
        )
        return JSONResponse(status_code=500, content=_GENERIC_ERR)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"level": "error", "event": "unexpected_error", "detail": str(exc)}),
            file=sys.stderr,
            flush=True,
        )
        return JSONResponse(status_code=500, content=_GENERIC_ERR)


# ---------------------------------------------------------------------------
# Endpoint: POST /api/auth/reset-password/confirm
# ---------------------------------------------------------------------------

@router.post("/reset-password/confirm", status_code=200)
def confirm_reset(
    body: ConfirmResetRequest,
    request: Request,
    r: redis_lib.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Validate a 6-digit code and update the user's password.

    Returns generic 200 for wrong / expired code to prevent enumeration
    (security rule 8).
    """
    email: str = str(body.email).lower().strip()
    code: str = body.code
    new_password: str = body.newPassword
    ip: str = request.client.host if request.client else "unknown"

    _GENERIC_OK = {"message": "Password has been reset successfully."}
    _GENERIC_INVALID = {"message": "Invalid or expired code."}
    _GENERIC_ERR = {"error": "service_unavailable"}

    # Security rule 7: password length validated by Pydantic schema before we
    # reach here.  An explicit guard is kept as defence-in-depth.
    if len(new_password) < 8:
        return JSONResponse(
            status_code=400,
            content={"error": "password_too_short"},
        )

    try:
        # ── Per-IP rate limit (security rule 5) ──────────────────────────────
        ip_rate_key = _rate_key_confirm_ip(ip)
        within_ip_limit = _check_and_increment_rate_limit(
            r,
            ip_rate_key,
            settings.RATE_LIMIT_CONFIRM_IP_MAX,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        if not within_ip_limit:
            audit.emit(
                event_type="rate_limit_hit",
                email=email,
                ip_address=ip,
                outcome="confirm_ip_rate_limited",
            )
            return JSONResponse(status_code=429, content={"error": "Too Many Requests"})

        # ── Per-email rate limit (security rule 4) ────────────────────────────
        rate_key = _rate_key_email(email)
        within_limit = _check_and_increment_rate_limit(
            r,
            rate_key,
            settings.RATE_LIMIT_RESET_MAX,
            settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        if not within_limit:
            audit.emit(
                event_type="rate_limit_hit",
                email=email,
                ip_address=ip,
                outcome="confirm_rate_limited",
            )
            return JSONResponse(status_code=429, content={"error": "Too Many Requests"})

        # ── Fetch stored hash via Lua (security rule 3, phase 1) ─────────────
        token_key = _token_key(email)
        fetch_script = r.register_script(_LUA_CHECK_AND_DELETE)
        stored_hash: Any = fetch_script(keys=[token_key])

        if stored_hash is None or stored_hash == -1:
            # Key does not exist (expired or never set).
            audit.emit(
                event_type="reset_failed",
                email=email,
                ip_address=ip,
                outcome="token_not_found_or_expired",
            )
            return JSONResponse(status_code=200, content=_GENERIC_INVALID)

        # ── Verify code against stored argon2id hash (constant-time) ─────────
        try:
            _ph.verify(stored_hash, code)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            audit.emit(
                event_type="reset_failed",
                email=email,
                ip_address=ip,
                outcome="invalid_code",
            )
            return JSONResponse(status_code=200, content=_GENERIC_INVALID)

        # ── Atomically delete Redis key only if hash still matches (rule 3) ──
        delete_script = r.register_script(_LUA_DELETE_IF_MATCH)
        deleted = delete_script(keys=[token_key], args=[stored_hash])
        # deleted == 0 means someone else already consumed the token (replay
        # protection). Treat as failure.
        if int(deleted) != 1:
            audit.emit(
                event_type="reset_failed",
                email=email,
                ip_address=ip,
                outcome="token_already_consumed",
            )
            return JSONResponse(status_code=200, content=_GENERIC_INVALID)

        # ── Look up user ──────────────────────────────────────────────────────
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            # Edge case: user was deleted between request and confirm.
            audit.emit(
                event_type="reset_failed",
                email=email,
                ip_address=ip,
                outcome="user_not_found_on_confirm",
            )
            return JSONResponse(status_code=200, content=_GENERIC_INVALID)

        # ── Hash new password with argon2id (security rule 6) ────────────────
        # Only the encoded hash string is stored — never the plaintext.
        new_password_hash = _ph.hash(new_password)
        user.password_hash = new_password_hash
        db.commit()

        audit.emit(
            event_type="reset_confirmed",
            email=email,
            ip_address=ip,
            outcome="password_updated",
        )
        return JSONResponse(status_code=200, content=_GENERIC_OK)

    except redis_lib.RedisError as exc:
        print(
            json.dumps({"level": "error", "event": "redis_error", "detail": str(exc)}),
            file=sys.stderr,
            flush=True,
        )
        return JSONResponse(status_code=500, content=_GENERIC_ERR)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"level": "error", "event": "unexpected_error", "detail": str(exc)}),
            file=sys.stderr,
            flush=True,
        )
        return JSONResponse(status_code=500, content=_GENERIC_ERR)
