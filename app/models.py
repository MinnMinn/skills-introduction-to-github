"""
SQLAlchemy ORM models.
"""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    # Stores the full Argon2id hash string produced by argon2-cffi.
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id!r} email=<redacted>>"
