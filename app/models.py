"""Pydantic request / response models for the profile-email endpoints."""
from pydantic import BaseModel, EmailStr, field_validator


class EmailChangeRequest(BaseModel):
    """Body for POST /api/profile/email — initiates the change flow."""
    new_email: EmailStr


class EmailConfirmRequest(BaseModel):
    """Body for POST /api/profile/email/confirm — validates the 6-digit code."""
    new_email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def code_must_be_six_digits(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("code must be exactly 6 digits")
        return v


class MessageResponse(BaseModel):
    message: str
