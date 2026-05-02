"""
Data-access layer.

All database interactions use the SQLAlchemy ORM which binds parameters
automatically — no user-supplied values are ever concatenated into query
strings (security policy rule 2).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_email(self, email: str) -> User | None:
        """
        Return the User whose email matches *email*, or None.

        Uses ORM filter() which issues a parameterised query —
        never string interpolation.
        """
        return (
            self._db.query(User)
            .filter(User.email == email)
            .first()
        )

    def create(self, email: str, plain_password: str) -> User:
        """
        Create and persist a new User with an Argon2id-hashed password.
        The plain-text password is hashed immediately and never stored.
        """
        user = User(
            email=email,
            hashed_password=hash_password(plain_password),
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
