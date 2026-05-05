"""API endpoints for user preferences.

Routes
------
GET  /api/v1/preferences/{user_id}  — return current preferences
PUT  /api/v1/preferences/{user_id}  — partial update of preferences
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.repos.preferences_repo import PreferencesRepository
from src.schemas.preferences import PreferencesResponse, PreferencesUpdateRequest

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


@router.get(
    "/{user_id}",
    response_model=PreferencesResponse,
    summary="Get user preferences",
)
async def get_preferences(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponse:
    """Return the stored preferences for *user_id*.

    Raises **404** if the user has no preferences record yet.
    """
    repo = PreferencesRepository(db)
    row = await repo.get(user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preferences for user '{user_id}' not found.",
        )
    return PreferencesResponse.model_validate(row)


@router.put(
    "/{user_id}",
    response_model=PreferencesResponse,
    summary="Update user preferences (partial)",
)
async def update_preferences(
    user_id: str,
    body: PreferencesUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponse:
    """Partially update preferences for *user_id*.

    Only the keys present in the request body are updated; existing keys that
    are absent from the payload are preserved.
    """
    repo = PreferencesRepository(db)
    row = await repo.upsert(user_id, body.preferences)
    return PreferencesResponse.model_validate(row)
