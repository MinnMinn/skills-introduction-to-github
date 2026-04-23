"""
Database models.

Tables:
  user_settings  — per-user application preferences
  orders         — customer orders

NOTE: Do NOT modify existing model schemas — they reflect live DB tables.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# UserSettings — user_settings table
# ---------------------------------------------------------------------------
# Columns:
#     user_id         TEXT PRIMARY KEY
#     theme           TEXT    (e.g. "light" | "dark")
#     language        TEXT    (e.g. "en", "fr")
#     notifications   BOOLEAN
#     timezone        TEXT    (e.g. "UTC", "America/New_York")
#     avatar_url      TEXT    (nullable — URL to user's avatar image)
#     updated_at      TEXT    (ISO-8601 timestamp, managed by the DB)
# ---------------------------------------------------------------------------


@dataclass
class UserSettings:
    """In-memory representation of a row in `user_settings`."""

    user_id: str
    theme: str = "light"
    language: str = "en"
    notifications: bool = True
    timezone: str = "UTC"
    avatar_url: Optional[str] = None
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Order — orders table
# ---------------------------------------------------------------------------
# Columns:
#     order_id    TEXT PRIMARY KEY  (UUID string)
#     product_id  TEXT              (UUID string)
#     quantity    INTEGER
#     price       TEXT              (decimal string to avoid float precision loss)
#     status      TEXT              (e.g. "pending")
#     created_at  TEXT              (ISO-8601 timestamp, managed by the DB)
# ---------------------------------------------------------------------------


@dataclass
class Order:
    """In-memory representation of a row in `orders`."""

    order_id: str
    product_id: str
    quantity: int
    price: str
    status: str = "pending"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
