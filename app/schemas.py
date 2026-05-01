"""
Pydantic v2 request / response schemas.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ConfirmResetRequest(BaseModel):
    email: EmailStr
    code: str
    newPassword: str

    @field_validator("code")
    @classmethod
    def code_must_be_six_digits(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("code must be exactly 6 digits")
        return v

    @field_validator("newPassword")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        # Security rule 7: reject passwords shorter than 8 characters.
        if len(v) < 8:
            raise ValueError("password_too_short")
        return v


class GenericSuccessResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
