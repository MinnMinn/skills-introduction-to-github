"""
Repository implementation for the `user_settings` table.

Equivalent of internal/repository/user_repo.go in the standard Go layout.

Isolates all data-access logic so the service/handler layers stay thin.
Uses an in-memory store by default; swap `_store` for a real DB session
in production without changing any business logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from internal.domain.repository import UserRepository
from internal.domain.user import UserSettings


class PreferencesRepository(UserRepository):
    """
    Concrete in-memory implementation of UserRepository.

    The `_store` class variable acts as the persistence layer during tests
    and local development.  In production this class would be instantiated
    with a real DB session/connection (e.g. SQLAlchemy, asyncpg).
    """

    # In-memory backing store keyed by user_id.
    # Replace with a real DB dependency for production.
    _store: Dict[str, UserSettings] = {}

    # ------------------------------------------------------------------
    # UserRepository contract
    # ------------------------------------------------------------------

    def get(self, user_id: str) -> Optional[UserSettings]:
        """Return the UserSettings for *user_id*, or None if not found."""
        return self._store.get(user_id)

    def update(self, user_id: str, fields: dict) -> Optional[UserSettings]:
        """
        Apply a partial update to the preferences of *user_id*.

        Returns the updated UserSettings, or None if the user doesn't exist.

        Raises:
            ValueError: if *fields* is empty.
        """
        if not fields:
            raise ValueError("No fields supplied for update")

        record = self._store.get(user_id)
        if record is None:
            return None

        for key, value in fields.items():
            if hasattr(record, key):
                setattr(record, key, value)

        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record

    # ------------------------------------------------------------------
    # Test / seed helpers (not part of the production interface)
    # ------------------------------------------------------------------

    def _seed(self, settings: UserSettings) -> None:
        """Insert or overwrite a record — used by tests only."""
        self._store[settings.user_id] = settings

    def _clear(self) -> None:
        """Remove all records — used by tests only."""
        self._store.clear()
