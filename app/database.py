"""
In-memory user store — acts as a thin abstraction over whatever real DB
would be wired up in production (e.g. SQLAlchemy / SQLModel).

Each record shape:
{
    "id": str,
    "email": str,                  # current (active) email
    "hashed_password": str,
    "previous_emails": [           # audit trail for old emails
        {"email": str, "valid_until": datetime}
    ]
}
"""
from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.config import OLD_EMAIL_VALID_DAYS

# ---------------------------------------------------------------------------
# In-memory store (swap for a real DB session in production)
# ---------------------------------------------------------------------------

_USERS: Dict[str, dict] = {}
_EMAIL_INDEX: Dict[str, str] = {}   # email -> user_id


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_user(email: str, hashed_password: str) -> dict:
    """Create and persist a new user record."""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "previous_emails": [],
    }
    _USERS[user_id] = user
    _EMAIL_INDEX[email] = user_id
    return deepcopy(user)


def get_user_by_id(user_id: str) -> Optional[dict]:
    user = _USERS.get(user_id)
    return deepcopy(user) if user else None


def get_user_by_email(email: str) -> Optional[dict]:
    """
    Looks up the user whose *current* email matches, OR whose previous email
    is still within the 30-day audit window.
    """
    # Current email fast-path
    user_id = _EMAIL_INDEX.get(email)
    if user_id:
        return deepcopy(_USERS[user_id])

    # Scan previous emails (audit trail)
    now = _now_utc()
    for user in _USERS.values():
        for prev in user.get("previous_emails", []):
            if prev["email"] == email and prev["valid_until"] > now:
                return deepcopy(user)

    return None


def update_user_email(user_id: str, new_email: str) -> Optional[dict]:
    """
    Change a user's email address.
    * Old email is kept valid for OLD_EMAIL_VALID_DAYS (audit trail).
    * Updates the email index atomically.
    """
    user = _USERS.get(user_id)
    if not user:
        return None

    old_email = user["email"]
    valid_until = _now_utc() + timedelta(days=OLD_EMAIL_VALID_DAYS)

    # Append old email to audit trail
    user["previous_emails"].append(
        {"email": old_email, "valid_until": valid_until}
    )

    # Update current email
    user["email"] = new_email

    # Update index
    _EMAIL_INDEX.pop(old_email, None)
    _EMAIL_INDEX[new_email] = user_id

    return deepcopy(user)


def clear_all() -> None:
    """Test helper — wipe all in-memory state."""
    _USERS.clear()
    _EMAIL_INDEX.clear()
