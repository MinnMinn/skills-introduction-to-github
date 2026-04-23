"""
Business logic for the User Preferences service.

Equivalent of internal/service/user_service.go in the standard Go layout.

The service layer sits between the handler (HTTP delivery) and the repository
(persistence).  It is responsible for orchestrating domain rules that go
beyond simple CRUD — e.g. authorisation checks, event emission, caching.

In this initial version the service delegates directly to the repository,
providing the correct architectural seam for future business logic without
adding unnecessary complexity.
"""

from __future__ import annotations

from typing import Optional

from internal.domain.repository import UserRepository
from internal.domain.user import UserSettings


class UserPreferencesService:
    """Orchestrates preference retrieval and updates.

    Args:
        repo: Any concrete implementation of UserRepository.
    """

    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def get_preferences(self, user_id: str) -> Optional[UserSettings]:
        """Return the preferences for *user_id*, or None if not found."""
        return self._repo.get(user_id)

    def update_preferences(
        self, user_id: str, fields: dict
    ) -> Optional[UserSettings]:
        """Apply a partial update to *user_id*'s preferences.

        Returns the updated record, or None if the user doesn't exist.

        Raises:
            ValueError: propagated from the repository when *fields* is empty.
        """
        return self._repo.update(user_id, fields)
