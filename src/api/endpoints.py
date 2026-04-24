"""
REST API endpoints for User Preferences.

Routes:
    GET  /api/v1/preferences/{user_id}  — return current preferences
    PUT  /api/v1/preferences/{user_id}  — partial update of preferences

Follows the repository pattern: all DB access goes through PreferencesRepository.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.db.repos.preferences_repo import PreferencesRepository
from src.schemas import PreferencesResponse, PreferencesUpdateRequest

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


# ---------------------------------------------------------------------------
# Dependency — allows tests to inject a custom repository instance
# ---------------------------------------------------------------------------

_default_repo = PreferencesRepository()


def get_repo() -> PreferencesRepository:
    return _default_repo


# ---------------------------------------------------------------------------
# GET /api/v1/preferences/{user_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}",
    response_model=PreferencesResponse,
    summary="Retrieve preferences for a user",
    responses={
        200: {"description": "Preferences returned successfully"},
        404: {"description": "User not found"},
    },
)
def get_preferences(
    user_id: str,
    repo: PreferencesRepository = Depends(get_repo),
) -> PreferencesResponse:
    """Return the stored preferences for *user_id*."""
    record = repo.get(user_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return PreferencesResponse(
        user_id=record.user_id,
        theme=record.theme,
        language=record.language,
        notifications=record.notifications,
        avatar_url=record.avatar_url,
        updated_at=record.updated_at,
    )


# ---------------------------------------------------------------------------
# PUT /api/v1/preferences/{user_id}
# ---------------------------------------------------------------------------


@router.put(
    "/{user_id}",
    response_model=PreferencesResponse,
    summary="Update preferences for a user (partial update supported)",
    responses={
        200: {"description": "Preferences updated successfully"},
        404: {"description": "User not found"},
        422: {"description": "Validation error in request body"},
    },
)
def update_preferences(
    user_id: str,
    payload: PreferencesUpdateRequest,
    repo: PreferencesRepository = Depends(get_repo),
) -> PreferencesResponse:
    """
    Apply a partial update to the preferences of *user_id*.

    Only the fields present in the request body are changed; omitted
    fields retain their current values.
    """
    if not payload.has_updates():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must contain at least one field to update",
        )

    # Build a dict of only the supplied (non-None) fields
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}

    record = repo.update(user_id, updates)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    return PreferencesResponse(
        user_id=record.user_id,
        theme=record.theme,
        language=record.language,
        notifications=record.notifications,
        avatar_url=record.avatar_url,
        updated_at=record.updated_at,
    )
