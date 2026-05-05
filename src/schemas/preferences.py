"""Pydantic schemas for the preferences API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class PreferencesResponse(BaseModel):
    """Response body returned by GET and PUT."""

    user_id: str
    preferences: dict[str, Any]

    model_config = {"from_attributes": True}


class PreferencesUpdateRequest(BaseModel):
    """Request body for PUT — all fields are optional (partial update)."""

    preferences: dict[str, Any]

    @field_validator("preferences")
    @classmethod
    def preferences_must_not_be_empty(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("preferences must be a JSON object")
        return v
