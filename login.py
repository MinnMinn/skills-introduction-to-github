"""
login.py – POST /login endpoint.

Security properties:
 - Passwords hashed with argon2id (t=3, m=65536, p=1).
 - Constant-time dummy verify when email is not found (prevents user enumeration).
 - Session tokens generated with secrets.token_hex(32) (CSPRNG).
 - Generic 401 for both unknown-email and wrong-password.
 - Password field is never logged.
 - All unhandled exceptions return a generic 500 body.
 - Rate limiting: 10 requests / IP / 60 s  and  5 failures / email / 60 s.
 - Session cookie (if used) emitted with Secure; HttpOnly; SameSite=Lax; Path=/.
"""

from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from flask import Flask, request, jsonify, Response

# ---------------------------------------------------------------------------
# Logging – request logs must never include the raw password.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def _redact_password(record: logging.LogRecord) -> bool:
    """Filter that removes any 'password' value from log messages."""
    if hasattr(record, "msg") and isinstance(record.msg, dict):
        record.msg = {
            k: ("***REDACTED***" if k == "password" else v)
            for k, v in record.msg.items()
        }
    return True


logger.addFilter(_redact_password)

# ---------------------------------------------------------------------------
# Argon2id hasher – t=3, m=65536, p=1 as required by security rules.
# ---------------------------------------------------------------------------
_PH = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

# Pre-computed dummy hash used for constant-time comparison when email is not
# found (prevents user-enumeration via timing side-channel).
_DUMMY_HASH: str = _PH.hash("__dummy_secret_that_will_never_match__")

# ---------------------------------------------------------------------------
# Minimal in-memory user store  { email: argon2id_hash }
# Replace with a real database in production.
# ---------------------------------------------------------------------------
_USER_STORE: dict[str, str] = {}


def register_user(email: str, password: str) -> None:
    """Hash *password* with argon2id and persist the hash."""
    _USER_STORE[email] = _PH.hash(password)


# ---------------------------------------------------------------------------
# Rate-limiting state  (in-memory; use Redis in production for multi-process)
# ---------------------------------------------------------------------------
_rl_lock = Lock()

# { ip: [(timestamp, …), …] }
_ip_requests: dict[str, list[float]] = defaultdict(list)

# { email: [(timestamp, is_failure), …] }
_email_failures: dict[str, list[float]] = defaultdict(list)

_IP_LIMIT = 10          # max requests per IP per window
_EMAIL_FAIL_LIMIT = 5   # max failures per email per window
_WINDOW = 60            # seconds


def _now() -> float:
    return time.monotonic()


def _prune(timestamps: list[float], window: float, now: float) -> list[float]:
    cutoff = now - window
    return [t for t in timestamps if t >= cutoff]


def _check_rate_limits(ip: str, email: str) -> tuple[bool, int]:
    """
    Returns (is_limited, retry_after_seconds).
    Side-effect: records this request for the given IP.
    """
    with _rl_lock:
        now = _now()

        # --- IP-based limit ---
        ip_ts = _prune(_ip_requests[ip], _WINDOW, now)
        if len(ip_ts) >= _IP_LIMIT:
            oldest = ip_ts[0]
            retry_after = int(_WINDOW - (now - oldest)) + 1
            _ip_requests[ip] = ip_ts
            return True, retry_after
        ip_ts.append(now)
        _ip_requests[ip] = ip_ts

        # --- Email-based failure limit (read-only check here; failures
        #     are recorded in the handler after a failed auth attempt) ---
        ef = _prune(_email_failures[email], _WINDOW, now)
        _email_failures[email] = ef
        if len(ef) >= _EMAIL_FAIL_LIMIT:
            oldest = ef[0]
            retry_after = int(_WINDOW - (now - oldest)) + 1
            return True, retry_after

    return False, 0


def _record_failure(email: str) -> None:
    with _rl_lock:
        now = _now()
        ef = _prune(_email_failures[email], _WINDOW, now)
        ef.append(now)
        _email_failures[email] = ef


# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login() -> Response:  # type: ignore[return]
    """Authenticate a user and return a session token."""
    try:
        # ------------------------------------------------------------------ #
        # 1. Parse & validate request body                                     #
        # ------------------------------------------------------------------ #
        data: Any = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "invalid_request", "detail": "JSON body required"}), 400

        missing = [f for f in ("email", "password") if not data.get(f)]
        if missing:
            return (
                jsonify(
                    {
                        "error": "missing_fields",
                        "detail": f"Required fields missing: {', '.join(missing)}",
                    }
                ),
                400,
            )

        email: str = data["email"]
        password: str = data["password"]

        # ------------------------------------------------------------------ #
        # 2. Rate-limit check                                                  #
        # ------------------------------------------------------------------ #
        client_ip: str = request.remote_addr or "unknown"
        is_limited, retry_after = _check_rate_limits(client_ip, email)
        if is_limited:
            resp = jsonify({"error": "too_many_requests"})
            resp.status_code = 429
            resp.headers["Retry-After"] = str(retry_after)
            return resp

        # ------------------------------------------------------------------ #
        # 3. Look up user & verify password                                   #
        # ------------------------------------------------------------------ #
        stored_hash = _USER_STORE.get(email)

        if stored_hash is None:
            # Equalise timing: verify against dummy hash even though we know
            # it will fail – prevents user-enumeration via response time.
            try:
                _PH.verify(_DUMMY_HASH, password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                pass
            _record_failure(email)
            return jsonify({"error": "invalid_credentials"}), 401

        try:
            _PH.verify(stored_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            _record_failure(email)
            return jsonify({"error": "invalid_credentials"}), 401

        # Rehash if argon2-cffi decides the parameters need updating.
        if _PH.check_needs_rehash(stored_hash):
            _USER_STORE[email] = _PH.hash(password)

        # ------------------------------------------------------------------ #
        # 4. Issue session token (CSPRNG)                                      #
        # ------------------------------------------------------------------ #
        token = secrets.token_hex(32)
        # NOTE: In production persist the token (e.g. Redis, signed JWT).
        # The raw token is intentionally NOT logged anywhere in this handler.

        response = jsonify({"token": token})
        # If the caller wants a cookie in addition to the JSON body, set it
        # with the required security attributes.
        response.set_cookie(
            "session",
            value=token,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/",
        )
        return response, 200

    except Exception:  # noqa: BLE001
        logger.exception("Unhandled error in /login handler")
        return jsonify({"error": "internal_error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Demo: pre-register a test user.
    register_user("alice@example.com", "supersecret")
    app.run(debug=False)
