"""Redis connection and helpers for email-change verification."""

import hashlib
import json
import logging
from typing import Optional

import redis as redis_lib

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level client — replaced in tests via dependency override
_redis: Optional[redis_lib.Redis] = None


def get_redis() -> redis_lib.Redis:
    """Return (and lazily create) the global Redis client."""
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis


def set_redis(client: redis_lib.Redis) -> None:
    """Override the global Redis client (used in tests)."""
    global _redis  # noqa: PLW0603
    _redis = client


# ── Key helpers ──────────────────────────────────────────────────────────────

def _email_hash(email: str) -> str:
    return hashlib.sha256(email.lower().encode()).hexdigest()


def _code_key(user_id: str, new_email: str) -> str:
    return f"email_change:{user_id}:{_email_hash(new_email)}"


def _attempts_key(user_id: str, new_email: str) -> str:
    return f"email_change_attempts:{user_id}:{_email_hash(new_email)}"


# ── Public helpers ────────────────────────────────────────────────────────────

def store_verification_code(user_id: str, new_email: str, code: str) -> None:
    """Store *code* in Redis with the configured TTL."""
    r = get_redis()
    key = _code_key(user_id, new_email)
    r.set(key, code, ex=settings.verification_code_ttl_seconds)
    # Reset any previous attempt counter when a new code is issued
    r.delete(_attempts_key(user_id, new_email))
    logger.debug("Stored verification code for user=%s key=%s", user_id, key)


def get_verification_code(user_id: str, new_email: str) -> Optional[str]:
    """Return the stored code, or None if absent / expired."""
    r = get_redis()
    return r.get(_code_key(user_id, new_email))


def increment_attempts(user_id: str, new_email: str) -> int:
    """Increment the wrong-attempt counter and return the new count.

    The attempts key is given the same TTL as the code so it expires together.
    """
    r = get_redis()
    key = _attempts_key(user_id, new_email)
    count = r.incr(key)
    # Ensure the attempts key expires; only set expiry on first increment
    if count == 1:
        r.expire(key, settings.verification_code_ttl_seconds)
    return int(count)


def get_attempts(user_id: str, new_email: str) -> int:
    """Return the current wrong-attempt count (0 if no key)."""
    r = get_redis()
    val = r.get(_attempts_key(user_id, new_email))
    return int(val) if val else 0


def delete_verification_keys(user_id: str, new_email: str) -> None:
    """Remove both the code and attempts keys after a successful confirmation."""
    r = get_redis()
    r.delete(_code_key(user_id, new_email))
    r.delete(_attempts_key(user_id, new_email))
