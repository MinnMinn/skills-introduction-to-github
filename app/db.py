"""
In-memory user store — replace with a real database in production.

Each user record:
{
    "id": str,
    "email": str,
    "hashed_password": str,
    "previous_emails": [{"email": str, "changed_at": datetime, "expires_at": datetime}],
}
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from app.config import OLD_EMAIL_GRACE_PERIOD_DAYS

# Keyed by user_id
_USERS: Dict[str, dict] = {}

# Secondary index: email → user_id  (includes previous emails during grace period)
_EMAIL_INDEX: Dict[str, str] = {}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_user(email: str, hashed_password: str) -> dict:
    """Create a new user and return the record."""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "previous_emails": [],
    }
    _USERS[user_id] = user
    _EMAIL_INDEX[email] = user_id
    return user


def get_user_by_id(user_id: str) -> Optional[dict]:
    return _USERS.get(user_id)


def get_user_by_email(email: str) -> Optional[dict]:
    """Look up a user by current *or* grace-period previous email."""
    user_id = _EMAIL_INDEX.get(email)
    if not user_id:
        return None
    user = _USERS.get(user_id)
    if not user:
        return None

    # If the email matches the current email, always valid.
    if user["email"] == email:
        return user

    # Check grace period for old emails.
    now = _now()
    for entry in user["previous_emails"]:
        if entry["email"] == email and entry["expires_at"] > now:
            return user

    return None


def update_user_email(user_id: str, new_email: str) -> Optional[dict]:
    """
    Update the user's current email and record the old one in the audit trail.
    The old email remains valid for login for OLD_EMAIL_GRACE_PERIOD_DAYS days.
    """
    user = _USERS.get(user_id)
    if not user:
        return None

    old_email = user["email"]
    now = _now()

    # Record old email in audit trail
    user["previous_emails"].append(
        {
            "email": old_email,
            "changed_at": now,
            "expires_at": now + timedelta(days=OLD_EMAIL_GRACE_PERIOD_DAYS),
        }
    )

    # Update primary record
    user["email"] = new_email
    _EMAIL_INDEX[new_email] = user_id
    # Keep old email in index (grace period)
    _EMAIL_INDEX[old_email] = user_id

    return user


def clear_all() -> None:
    """Test helper — reset all state."""
    _USERS.clear()
    _EMAIL_INDEX.clear()
