"""In-memory user store (stub database).

Provides the minimal surface needed for the email-change flow:
- look up a user by ID
- update the user's primary email
- retain old emails for 30 days (audit trail)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class UserRecord:
    def __init__(self, user_id: str, email: str, hashed_password: str = "hashed"):
        self.user_id: str = user_id
        self.email: str = email
        self.hashed_password: str = hashed_password
        # Audit trail: list of {"email": ..., "changed_at": ..., "expires_at": ...}
        self.previous_emails: List[Dict] = []

    def __repr__(self) -> str:
        return f"<UserRecord id={self.user_id} email={self.email}>"


# Seed data — two users available for tests / manual testing
_USERS: Dict[str, UserRecord] = {
    "user-001": UserRecord("user-001", "alice@example.com"),
    "user-002": UserRecord("user-002", "bob@example.com"),
}


def get_user(user_id: str) -> Optional[UserRecord]:
    """Return the UserRecord for *user_id*, or None."""
    return _USERS.get(user_id)


def update_user_email(user_id: str, new_email: str) -> bool:
    """Update the user's primary email and record the old one in the audit trail.

    Returns True on success, False if the user does not exist.
    """
    user = _USERS.get(user_id)
    if user is None:
        return False

    now = datetime.now(tz=timezone.utc)
    retention_delta = timedelta(days=settings.old_email_retention_days)

    # Archive the current email
    user.previous_emails.append(
        {
            "email": user.email,
            "changed_at": now.isoformat(),
            "expires_at": (now + retention_delta).isoformat(),
        }
    )
    logger.info(
        "Email change audit: user=%s old=%s new=%s expires=%s",
        user_id,
        user.email,
        new_email,
        (now + retention_delta).isoformat(),
    )
    user.email = new_email
    return True


def email_exists_in_audit(user_id: str, email: str) -> bool:
    """Return True if *email* is in the user's active audit-trail entries (not yet expired).

    An old email is considered 'still valid for login' as long as its retention period
    has not elapsed.  The actual login check would call this helper.
    """
    user = _USERS.get(user_id)
    if user is None:
        return False

    now = datetime.now(tz=timezone.utc)
    for entry in user.previous_emails:
        expires_at = datetime.fromisoformat(entry["expires_at"])
        if entry["email"] == email and now < expires_at:
            return True
    return False


def reset_db() -> None:
    """Re-seed the in-memory store — used in tests."""
    global _USERS  # noqa: PLW0603
    _USERS = {
        "user-001": UserRecord("user-001", "alice@example.com"),
        "user-002": UserRecord("user-002", "bob@example.com"),
    }
