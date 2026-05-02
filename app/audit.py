"""
Structured audit logging for authentication events.

Every login attempt emits a JSON log entry containing:
  - ISO-8601 timestamp
  - outcome: "success" | "failure"
  - email_sha256: SHA-256 of the email address (never plaintext PII)
  - source_ip: remote IP of the caller
  - http_status: the HTTP status code returned to the client

Passwords and raw JWT values are NEVER logged anywhere in this module
or by the logging framework (no full-body serialisation).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger("audit.login")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def emit_login_audit(
    *,
    outcome: Literal["success", "failure"],
    email: str,
    source_ip: str,
    http_status: int,
) -> None:
    """
    Emit a structured JSON audit log entry.

    :param outcome:     "success" or "failure"
    :param email:       The email submitted (hashed before logging)
    :param source_ip:   Caller's IP address
    :param http_status: HTTP response status code sent to the client
    """
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "event": "login_attempt",
        "outcome": outcome,
        "email_sha256": _sha256_hex(email),
        "source_ip": source_ip,
        "http_status": http_status,
    }
    # Use INFO level so audit entries are always emitted; the logging
    # configuration should route this logger to a persistent audit sink.
    logger.info(json.dumps(entry))
