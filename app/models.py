"""Pydantic request / response models."""
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class EmailChangeRequest(BaseModel):
    new_email: EmailStr = Field(..., description="The new email address to set.")


class EmailConfirmRequest(BaseModel):
    new_email: EmailStr = Field(..., description="The new email address to confirm.")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code.")


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
