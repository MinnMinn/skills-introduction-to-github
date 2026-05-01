"""
Audit trail for email changes.

In a real application this module would update a database (e.g. SQLAlchemy /
asyncpg).  Here it stubs the DB layer and logs all mutations so the
acceptance criteria can be verified without a running database.

Acceptance criterion: the old email must still work for login for 30 days.
This is represented by the ``old_email_valid_until`` field in the user record.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from app.config import OLD_EMAIL_GRACE_DAYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory "database" for development / testing.
# Replace with real DB access in production.
# ---------------------------------------------------------------------------
_USERS: Dict[str, Dict[str, Any]] = {}


def get_user(user_id: str) -> Dict[str, Any] | None:
    """Return the user record or None if not found."""
    return _USERS.get(user_id)


def upsert_user(user_id: str, email: str) -> None:
    """Create or update a user record (used in tests to seed data)."""
    _USERS[user_id] = {"user_id": user_id, "email": email}


def update_user_email(user_id: str, new_email: str) -> None:
    """
    Update the user's primary email and record the old email with a 30-day
    grace-period expiry (audit trail / backward-compatibility requirement).
    """
    user = _USERS.get(user_id)
    if user is None:
        # User should exist at this point; log and bail rather than silently
        # creating a record with potentially wrong data.
        logger.error("update_user_email called for unknown user_id=%s", user_id)
        return

    old_email = user.get("email")
    grace_until = datetime.now(tz=timezone.utc) + timedelta(days=OLD_EMAIL_GRACE_DAYS)

    _USERS[user_id] = {
        **user,
        "email": new_email,
        "old_email": old_email,
        "old_email_valid_until": grace_until.isoformat(),
    }

    logger.info(
        "AUDIT — user %s email changed from %s to %s; old email valid until %s",
        user_id,
        old_email,
        new_email,
        grace_until.isoformat(),
    )
