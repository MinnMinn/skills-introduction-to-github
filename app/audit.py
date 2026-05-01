"""
Structured audit logging.

All audit lines are emitted as single-line JSON to stdout.
Security rule 11: fields are timestamp (ISO-8601 UTC), event_type,
email_hash (hex SHA-256 of email — never plaintext), ip_address, outcome.
Plaintext email, plaintext code, and password hashes MUST NOT appear here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from typing import Literal

EventType = Literal[
    "reset_requested",
    "reset_confirmed",
    "reset_failed",
    "rate_limit_hit",
]


def _sha256_hex(value: str) -> str:
    """Return the hex-encoded SHA-256 digest of *value*."""
    return hashlib.sha256(value.encode()).hexdigest()


def emit(
    *,
    event_type: EventType,
    email: str,
    ip_address: str,
    outcome: str,
) -> None:
    """Write one structured audit JSON line to stdout.

    The plaintext email is hashed; it is NEVER written to the audit log.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "email_hash": _sha256_hex(email),
        "ip_address": ip_address,
        "outcome": outcome,
    }
    print(json.dumps(record), file=sys.stdout, flush=True)
