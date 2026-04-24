"""
Pydantic request / response schemas.

Sections:
  - Preferences API  (PreferencesResponse, PreferencesUpdateRequest)
  - Orders API       (OrderCreateRequest, OrderResponse)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Preferences — Response schema
# ---------------------------------------------------------------------------


class PreferencesResponse(BaseModel):
    """Full preferences object returned by GET and PUT."""

    user_id: str
    theme: Literal["light", "dark"]
    language: str
    notifications: bool
    avatar_url: Optional[str] = None
    updated_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Preferences — Request schema (partial update — all fields optional)
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
    avatar_url: Optional[AnyHttpUrl] = None

    @field_validator("language")
    @classmethod
    def language_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("language must not be blank")
        return v

    @field_validator("avatar_url", mode="before")
    @classmethod
    def avatar_url_to_str(cls, v: object) -> object:
        """Pass-through; Pydantic's AnyHttpUrl already validates the URL format."""
        return v

    def has_updates(self) -> bool:
        """Return True if at least one field was supplied."""
        return any(v is not None for v in self.model_dump().values())

    def model_dump_updates(self) -> dict:
        """
        Return only the non-None fields, converting AnyHttpUrl values to plain
        strings so the repository layer stays URL-type-agnostic.
        """
        result = {}
        for k, v in self.model_dump().items():
            if v is not None:
                result[k] = str(v) if k == "avatar_url" else v
        return result


# ---------------------------------------------------------------------------
# Orders — Request schema
# ---------------------------------------------------------------------------


class OrderCreateRequest(BaseModel):
    """
    Payload accepted by POST /api/v1/orders.

    Validation rules:
      - product_id  : must be a valid UUID v4 string
      - quantity    : integer strictly greater than 0
      - price       : decimal >= 0.01
    """

    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Number of units ordered; must be > 0")
    price: Decimal = Field(..., ge=Decimal("0.01"), description="Unit price; must be >= 0.01")


# ---------------------------------------------------------------------------
# Orders — Response schema
# ---------------------------------------------------------------------------


class OrderResponse(BaseModel):
    """Order object returned after a successful creation."""

    order_id: str
    product_id: str
    quantity: int
    price: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}
