"""In-memory user store (stub — replace with a real DB in production).

Each user record looks like::

    {
        "id": "u1",
        "email": "current@example.com",
        "hashed_password": "...",
        "email_audit": [
            {
                "old_email": "previous@example.com",
                "changed_at": <datetime>,
                "expires_at": <datetime>,   # old_email valid for login until this date
            }
        ]
    }
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.core.config import settings

# ── Stub in-memory "database" ──────────────────────────────────────────────
_users: Dict[str, dict] = {
    "u1": {
        "id": "u1",
        "email": "user@example.com",
        "hashed_password": "hashed_password_stub",
        "email_audit": [],
    }
}


# ── CRUD helpers ───────────────────────────────────────────────────────────

def get_user_by_id(user_id: str) -> Optional[dict]:
    return _users.get(user_id)


def get_user_by_email(email: str) -> Optional[dict]:
    """Return the user whose *current* email matches (case-insensitive)."""
    email_lower = email.lower()
    for user in _users.values():
        if user["email"].lower() == email_lower:
            return user
    return None


def update_user_email(user_id: str, new_email: str) -> None:
    """Update the user's email and record the old address in the audit log."""
    user = _users[user_id]
    old_email = user["email"]
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(days=settings.OLD_EMAIL_RETENTION_DAYS)

    user["email_audit"].append(
        {
            "old_email": old_email,
            "changed_at": now,
            "expires_at": expires_at,
        }
    )
    user["email"] = new_email


def email_valid_for_login(user_id: str, email: str) -> bool:
    """Return True if *email* is valid for login (current OR still-live old)."""
    user = _users.get(user_id)
    if not user:
        return False
    if user["email"].lower() == email.lower():
        return True
    now = datetime.now(tz=timezone.utc)
    for entry in user.get("email_audit", []):
        if (
            entry["old_email"].lower() == email.lower()
            and entry["expires_at"] > now
        ):
            return True
    return False


# ── Test helper ────────────────────────────────────────────────────────────

def _reset_store(users: Optional[Dict[str, dict]] = None) -> None:  # pragma: no cover
    """Replace the in-memory store (used in tests)."""
    global _users
    _users = users or {
        "u1": {
            "id": "u1",
            "email": "user@example.com",
            "hashed_password": "hashed_password_stub",
            "email_audit": [],
        }
    }
