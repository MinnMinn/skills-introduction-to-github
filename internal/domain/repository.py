"""
Repository interface for the User Preferences bounded context.

Equivalent of internal/domain/repository.go in the standard Go layout.

Defines the abstract contract that any persistence implementation must
satisfy.  The service and handler layers depend only on this interface,
making it easy to swap the backing store (in-memory → PostgreSQL, etc.)
without touching business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from internal.domain.user import UserSettings


class UserRepository(ABC):
    """Abstract repository contract for UserSettings persistence."""

    @abstractmethod
    def get(self, user_id: str) -> Optional[UserSettings]:
        """Return the UserSettings for *user_id*, or None if not found."""
        ...

    @abstractmethod
    def update(self, user_id: str, fields: dict) -> Optional[UserSettings]:
        """Apply a partial update; return updated record or None if not found.

        Raises:
            ValueError: if *fields* is empty.
        """
        ...
