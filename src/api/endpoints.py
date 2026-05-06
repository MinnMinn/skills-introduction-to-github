"""API route handlers for the preferences resource."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Preferences
from src.schemas import PreferencesResponse, PreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/{user_id}", response_model=PreferencesResponse)
def get_preferences(user_id: int, db: Session = Depends(get_db)) -> PreferencesResponse:
    """Return preferences for *user_id*.

    ``avatar_url`` defaults to ``None`` when not set.
    Raises HTTP 404 if the user has no preferences row yet.
    """
    prefs = db.query(Preferences).filter(Preferences.user_id == user_id).first()
    if prefs is None:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return PreferencesResponse.model_validate(prefs)


@router.patch("/{user_id}", response_model=PreferencesResponse)
def update_preferences(
    user_id: int,
    payload: PreferencesUpdate,
    db: Session = Depends(get_db),
) -> PreferencesResponse:
    """Partially update preferences for *user_id*.

    Creates a new row with defaults when one does not exist yet.
    Raises HTTP 422 (automatically, via Pydantic) for an invalid ``avatar_url``.
    """
    prefs = db.query(Preferences).filter(Preferences.user_id == user_id).first()
    if prefs is None:
        prefs = Preferences(user_id=user_id)
        db.add(prefs)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)
    return PreferencesResponse.model_validate(prefs)
