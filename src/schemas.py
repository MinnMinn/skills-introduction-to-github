"""Pydantic request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, HttpUrl, field_validator


class PreferencesResponse(BaseModel):
    """Schema returned by GET /preferences/{user_id}.

    Note: `timezone` has been intentionally omitted per KAN-8.
    """

    user_id: int
    theme: str
    language: str
    notifications: bool
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class PreferencesUpdate(BaseModel):
    """Schema accepted by PATCH /preferences/{user_id}.

    All fields are optional so callers can update only what they need.
    """

    theme: str | None = None
    language: str | None = None
    notifications: bool | None = None
    avatar_url: str | None = None

    @field_validator("avatar_url", mode="before")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Validate that avatar_url is a well-formed HTTP/HTTPS URL when provided."""
        if v is None:
            return v
        # Delegate to Pydantic's HttpUrl for robust validation.
        HttpUrl(v)  # raises ValueError on invalid URL
        return v
