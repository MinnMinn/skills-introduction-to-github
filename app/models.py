"""
SQLAlchemy ORM models.
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    # Only the argon2id-encoded hash is stored — never the plaintext password.
    password_hash = Column(String, nullable=False)
