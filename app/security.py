"""
Security utilities: password hashing and JWT generation/verification.

Password hashing policy
-----------------------
  Algorithm : Argon2id
  Parameters: time_cost=3, memory_cost=65536 KiB (64 MiB), parallelism=1
  Fallback  : If argon2-cffi is unavailable at runtime the service refuses
              to start rather than silently downgrading to a weaker hash.

JWT policy
----------
  Algorithm : HS256
  Secret    : loaded exclusively from the JWT_SECRET environment variable
              (≥ 32 bytes / 256 bits).
  Claims    : sub (stable user identifier) + exp only.
  Expiry    : ≤ 3600 seconds (enforced in config).
"""
from __future__ import annotations

from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import jwt

from app.config import get_settings

# ---------------------------------------------------------------------------
# Argon2id hasher — t=3, m=65536, p=1 as required by security policy.
# ---------------------------------------------------------------------------
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """Return an Argon2id hash string for *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True iff *plain* matches *hashed*.

    Uses the library's constant-time verify — never short-circuits on
    intermediate hash bytes.  All exception types (mismatch, invalid hash,
    verification error) are caught and mapped to False so the call site
    always sees a boolean without leaking internal detail.
    """
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(subject: str) -> str:
    """
    Create a signed HS256 JWT for *subject* (the stable user identifier).

    Payload contains only 'sub' and 'exp' — no roles, permissions, or
    admin flags are embedded per security policy rule 6.
    """
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    exp = now.timestamp() + settings.jwt_expiry_seconds
    payload = {
        "sub": subject,
        "exp": int(exp),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
