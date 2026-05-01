"""Pydantic request / response models."""

from pydantic import BaseModel, EmailStr


class EmailChangeRequest(BaseModel):
    new_email: EmailStr


class EmailConfirmRequest(BaseModel):
    new_email: EmailStr
    code: str


class MessageResponse(BaseModel):
    detail: str
