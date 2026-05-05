"""SQLAlchemy ORM models.

Uses the existing `user_settings` table — schema is NOT modified here.
"""
from __future__ import annotations

from sqlalchemy import Column, JSON, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserSettings(Base):
    """Maps to the existing `user_settings` table."""

    __tablename__ = "user_settings"

    user_id: str = Column(String, primary_key=True, index=True)
    preferences: dict = Column(JSON, nullable=False, default=dict)
