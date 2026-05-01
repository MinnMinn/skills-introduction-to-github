"""
Verification-code service.

Responsibilities:
* Generate a cryptographically random 6-digit code.
* Store it in Redis keyed by ``{user_id}:{sha256(new_email)}`` with a 15-min TTL.
* Validate a supplied code and enforce a 5-attempt rate limit per key.
* Delete the code on successful verification.
"""
from __future__ import annotations

import hashlib
import logging
import secrets

import redis as redis_lib

from app.config import MAX_VERIFY_ATTEMPTS, VERIFICATION_CODE_TTL_SECONDS

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Internal key helpers
# -------------------------------------------------------------------------

def _code_key(user_id: str, new_email: str) -> str:
    email_hash = hashlib.sha256(new_email.lower().encode()).hexdigest()
    return f"email_verify:code:{user_id}:{email_hash}"


def _attempts_key(user_id: str, new_email: str) -> str:
    email_hash = hashlib.sha256(new_email.lower().encode()).hexdigest()
    return f"email_verify:attempts:{user_id}:{email_hash}"


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------

def generate_and_store_code(
    r: redis_lib.Redis, user_id: str, new_email: str
) -> str:
    """
    Generate a 6-digit code, persist it to Redis with TTL, and return it.
    Any existing code + attempt counter for the same (user, email) pair are
    replaced atomically so that re-requesting a code resets the clock.
    """
    code = str(secrets.randbelow(10**6)).zfill(6)

    code_k = _code_key(user_id, new_email)
    att_k = _attempts_key(user_id, new_email)

    pipe = r.pipeline()
    pipe.set(code_k, code, ex=VERIFICATION_CODE_TTL_SECONDS)
    pipe.delete(att_k)          # reset attempt counter on new code
    pipe.execute()

    logger.debug("Stored verification code for user=%s email=%s", user_id, new_email)
    return code


def verify_code(
    r: redis_lib.Redis, user_id: str, new_email: str, supplied_code: str
) -> tuple[bool, bool]:
    """
    Validate *supplied_code* against the stored code.

    Returns ``(is_valid, is_rate_limited)`` where:
    * ``is_rate_limited`` is ``True`` when the caller has exceeded
      ``MAX_VERIFY_ATTEMPTS`` wrong guesses (regardless of *is_valid*).
    * ``is_valid`` is ``True`` only when the code matches AND the attempt
      limit has not been breached.

    On a **successful** match the code and the attempt counter are removed
    from Redis so the code cannot be reused.
    """
    code_k = _code_key(user_id, new_email)
    att_k = _attempts_key(user_id, new_email)

    stored_code = r.get(code_k)

    if stored_code is None:
        # Code expired or never issued — treat as wrong attempt but don't
        # increment a missing counter (there is nothing to rate-limit against).
        return False, False

    # Check attempt count BEFORE comparing so an attacker can't brute-force
    # the last attempt after the counter hits the threshold.
    attempts = int(r.get(att_k) or 0)
    if attempts >= MAX_VERIFY_ATTEMPTS:
        logger.warning(
            "Rate limit exceeded for user=%s email_verify", user_id
        )
        return False, True

    if secrets.compare_digest(stored_code, supplied_code.strip()):
        # Success — clean up
        pipe = r.pipeline()
        pipe.delete(code_k)
        pipe.delete(att_k)
        pipe.execute()
        return True, False

    # Wrong code — increment attempt counter (TTL mirrors the code TTL)
    pipe = r.pipeline()
    pipe.incr(att_k)
    pipe.expire(att_k, VERIFICATION_CODE_TTL_SECONDS)
    pipe.execute()

    new_attempts = attempts + 1
    if new_attempts >= MAX_VERIFY_ATTEMPTS:
        logger.warning(
            "User=%s has now reached the rate limit for email verification", user_id
        )
        return False, True

    return False, False
