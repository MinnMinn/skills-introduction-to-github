"""SQLAlchemy ORM models."""
from sqlalchemy import Boolean, Column, Integer, String

from src.db.database import Base


class Preferences(Base):
    """User preferences stored in the database."""

    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    theme = Column(String, nullable=False, default="light")
    language = Column(String, nullable=False, default="en")
    notifications = Column(Boolean, nullable=False, default=True)
    avatar_url = Column(String, nullable=True, default=None)
