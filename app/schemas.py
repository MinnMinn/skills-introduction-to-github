"""
Pydantic schemas for request validation and response serialisation.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request body for POST /api/login."""

    email: EmailStr = Field(..., description="Registered user email address.")
    password: str = Field(..., min_length=1, description="Account password.")

    model_config = {
        # Forbid extra fields to prevent parameter pollution.
        "extra": "forbid",
    }


class LoginResponse(BaseModel):
    """Successful login response — contains the signed JWT session token."""

    token: str = Field(..., description="Signed HS256 JWT session token.")
