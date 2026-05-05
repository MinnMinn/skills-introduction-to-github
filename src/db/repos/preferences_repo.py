"""Repository for user preferences stored in the `user_settings` table."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import UserSettings


class PreferencesRepository:
    """Encapsulates all database access for user preferences."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, user_id: str) -> Optional[UserSettings]:
        """Return the UserSettings row for *user_id*, or None if absent."""
        result = await self._db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, patch: dict) -> UserSettings:
        """Partially update preferences for *user_id*.

        If no row exists yet, create one.  Only the keys present in *patch*
        are overwritten; all other existing keys are preserved.
        """
        row = await self.get(user_id)
        if row is None:
            row = UserSettings(user_id=user_id, preferences={})
            self._db.add(row)

        # Merge: existing keys not in patch are kept unchanged.
        updated = {**(row.preferences or {}), **patch}
        row.preferences = updated

        await self._db.commit()
        await self._db.refresh(row)
        return row
