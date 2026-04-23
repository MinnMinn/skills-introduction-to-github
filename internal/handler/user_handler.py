"""
HTTP handlers (delivery layer) for User Preferences.

Equivalent of internal/handler/user_handler.go in the standard Go layout.

Routes:
    GET  /api/v1/preferences/{user_id}  — return current preferences
    PUT  /api/v1/preferences/{user_id}  — partial update of preferences

Follows the dependency-injection pattern: all business logic goes through
UserPreferencesService; all DB access goes through PreferencesRepository.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from internal.domain.schemas import PreferencesResponse, PreferencesUpdateRequest
from internal.repository.user_repo import PreferencesRepository
from internal.service.user_service import UserPreferencesService

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


# ---------------------------------------------------------------------------
# Dependency wiring — allows tests to inject custom instances
# ---------------------------------------------------------------------------

_default_repo = PreferencesRepository()


def get_repo() -> PreferencesRepository:
    """FastAPI dependency that returns the shared repository instance."""
    return _default_repo


def get_service(
    repo: PreferencesRepository = Depends(get_repo),
) -> UserPreferencesService:
    """FastAPI dependency that returns a service wired to *repo*."""
    return UserPreferencesService(repo)


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
    service: UserPreferencesService = Depends(get_service),
) -> PreferencesResponse:
    """Return the stored preferences for *user_id*."""
    record = service.get_preferences(user_id)
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
        timezone=record.timezone,
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
    service: UserPreferencesService = Depends(get_service),
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

    record = service.update_preferences(user_id, updates)
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
        timezone=record.timezone,
        updated_at=record.updated_at,
    )
