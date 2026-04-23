"""
Pydantic request / response schemas for the Preferences API.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class PreferencesResponse(BaseModel):
    """Full preferences object returned by GET and PUT."""

    user_id: str
    theme: Literal["light", "dark"]
    language: str
    notifications: bool
    timezone: str
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schema (partial update — all fields optional)
# ---------------------------------------------------------------------------


class PreferencesUpdateRequest(BaseModel):
    """
    Payload accepted by PUT /api/v1/preferences/{user_id}.

    All fields are optional so that callers can perform a partial update
    (PATCH-style semantics over PUT).  At least one field must be present.
    """

    theme: Optional[Literal["light", "dark"]] = None
    language: Optional[str] = None
    notifications: Optional[bool] = None
    timezone: Optional[str] = None

    @field_validator("language")
    @classmethod
    def language_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("language must not be blank")
        return v

    @field_validator("timezone")
    @classmethod
    def timezone_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("timezone must not be blank")
        return v

    def has_updates(self) -> bool:
        """Return True if at least one field was supplied."""
        return any(v is not None for v in self.model_dump().values())
