"""
Redis helpers for the email-change verification flow.

Key layout
----------
verify:{hash}        → 6-digit code string       TTL = VERIFY_CODE_TTL_SECONDS
verify_attempts:{hash} → integer attempt counter  TTL = VERIFY_CODE_TTL_SECONDS
"""
from __future__ import annotations

import hashlib
import random
import string
from typing import Optional

import redis as redis_lib

from app.config import REDIS_URL, VERIFY_CODE_MAX_ATTEMPTS, VERIFY_CODE_TTL_SECONDS

# Module-level client — can be swapped out in tests via dependency injection.
_redis_client: Optional[redis_lib.Redis] = None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def set_redis(client: redis_lib.Redis) -> None:
    """Allow tests to inject a fake Redis instance."""
    global _redis_client
    _redis_client = client


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------

def _make_key(user_id: str, new_email: str) -> str:
    """Deterministic, non-reversible key derived from user_id + new_email."""
    raw = f"{user_id}:{new_email}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return f"verify:{digest}"


def _attempts_key(user_id: str, new_email: str) -> str:
    raw = f"{user_id}:{new_email}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return f"verify_attempts:{digest}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_code() -> str:
    """Return a cryptographically-adequate 6-digit string."""
    return "".join(random.SystemRandom().choices(string.digits, k=6))


def store_verification_code(user_id: str, new_email: str, code: str) -> None:
    """Store *code* in Redis, replacing any existing entry (re-send flow)."""
    r = get_redis()
    key = _make_key(user_id, new_email)
    att_key = _attempts_key(user_id, new_email)
    pipe = r.pipeline()
    pipe.set(key, code, ex=VERIFY_CODE_TTL_SECONDS)
    # Reset attempt counter on fresh code issuance
    pipe.delete(att_key)
    pipe.execute()


def verify_code(user_id: str, new_email: str, submitted_code: str) -> bool:
    """
    Check *submitted_code* against the stored value.

    Returns True on match.
    Raises RateLimitExceeded after VERIFY_CODE_MAX_ATTEMPTS failures.
    Raises CodeNotFound if no code exists (expired or never issued).
    """
    r = get_redis()
    key = _make_key(user_id, new_email)
    att_key = _attempts_key(user_id, new_email)

    stored = r.get(key)
    if stored is None:
        raise CodeNotFound("No pending verification code found.")

    # Check rate limit *before* revealing whether code is correct
    attempts = int(r.get(att_key) or 0)
    if attempts >= VERIFY_CODE_MAX_ATTEMPTS:
        raise RateLimitExceeded(
            f"Too many failed attempts. Please request a new code."
        )

    if stored != submitted_code:
        # Increment attempt counter (expire aligned with the code TTL)
        ttl = r.ttl(key)
        r.set(att_key, attempts + 1, ex=max(ttl, 1))
        raise InvalidCode("Verification code is incorrect.")

    # Success — clean up
    pipe = r.pipeline()
    pipe.delete(key)
    pipe.delete(att_key)
    pipe.execute()
    return True


def delete_verification_code(user_id: str, new_email: str) -> None:
    r = get_redis()
    pipe = r.pipeline()
    pipe.delete(_make_key(user_id, new_email))
    pipe.delete(_attempts_key(user_id, new_email))
    pipe.execute()


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class CodeNotFound(Exception):
    pass


class InvalidCode(Exception):
    pass


class RateLimitExceeded(Exception):
    pass
