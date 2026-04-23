"""
Domain entities for the User Preferences bounded context.

Equivalent of internal/domain/user.go in the standard Go layout.

Defines the core business entity (UserSettings) and its default values.
This module has zero dependencies on framework or infrastructure code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class UserSettings:
    """In-memory representation of a row in `user_settings`.

    This is the canonical domain entity — all layers share this type.
    The repository layer persists it; the handler layer serialises it
    into HTTP responses via the schema layer.

    Attributes:
        user_id:       Unique identifier for the user.
        theme:         UI colour scheme — "light" or "dark".
        language:      BCP-47 language tag (e.g. "en", "fr").
        notifications: Whether push notifications are enabled.
        timezone:      IANA timezone string (e.g. "UTC", "Europe/Paris").
        updated_at:    ISO-8601 timestamp of the last modification.
    """

    user_id: str
    theme: str = "light"
    language: str = "en"
    notifications: bool = True
    timezone: str = "UTC"
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
