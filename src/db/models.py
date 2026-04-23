"""
Database models for the user_settings table.

NOTE: Do NOT modify this schema — it reflects the existing `user_settings` table.
Columns:
    user_id         TEXT PRIMARY KEY
    theme           TEXT    (e.g. "light" | "dark")
    language        TEXT    (e.g. "en", "fr")
    notifications   BOOLEAN
    timezone        TEXT    (e.g. "UTC", "America/New_York")
    updated_at      TEXT    (ISO-8601 timestamp, managed by the DB)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserSettings:
    """In-memory representation of a row in `user_settings`."""

    user_id: str
    theme: str = "light"
    language: str = "en"
    notifications: bool = True
    timezone: str = "UTC"
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
