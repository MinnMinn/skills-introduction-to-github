"""
Simple Redis-backed attempt counter for the email-confirm endpoint.

After MAX_CONFIRM_ATTEMPTS wrong codes the counter stays in Redis for the
remainder of the TTL so the user cannot retry until the verification window
expires (effectively invalidating the pending request).
"""
from __future__ import annotations

import logging

import redis as _redis_lib

from app.config import MAX_CONFIRM_ATTEMPTS, VERIFICATION_CODE_TTL_SECONDS

logger = logging.getLogger(__name__)

_ATTEMPT_PREFIX = "email_confirm_attempts:"


def _attempt_key(user_id: str, new_email: str) -> str:
    return f"{_ATTEMPT_PREFIX}{user_id}:{new_email}"


def increment_attempt(r: _redis_lib.Redis, user_id: str, new_email: str) -> int:
    """
    Increment the wrong-attempt counter and return the new count.
    Sets a TTL equal to the verification window on first increment.
    """
    key = _attempt_key(user_id, new_email)
    count = r.incr(key)
    if count == 1:
        # Set expiry only on the first attempt so the window is bounded.
        r.expire(key, VERIFICATION_CODE_TTL_SECONDS)
    logger.debug("Wrong confirm attempt count for user %s: %d", user_id, count)
    return int(count)


def is_rate_limited(r: _redis_lib.Redis, user_id: str, new_email: str) -> bool:
    """Return True if the user has exceeded the allowed wrong-attempt count."""
    key = _attempt_key(user_id, new_email)
    raw = r.get(key)
    if raw is None:
        return False
    return int(raw) >= MAX_CONFIRM_ATTEMPTS


def reset_attempts(r: _redis_lib.Redis, user_id: str, new_email: str) -> None:
    """Delete the attempt counter after a successful confirmation."""
    r.delete(_attempt_key(user_id, new_email))
