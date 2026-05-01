"""Database models: User and AuditLog."""
from datetime import datetime, timezone

import bcrypt

from .extensions import db


class User(db.Model):
    """Represents an application user.

    Passwords are stored as bcrypt hashes — the plaintext is never persisted.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------ #
    # Password helpers                                                     #
    # ------------------------------------------------------------------ #

    def set_password(self, plaintext: str) -> None:
        """Hash *plaintext* with bcrypt and store the result.

        Args:
            plaintext: The user's raw password.
        """
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(
            plaintext.encode("utf-8"), salt
        ).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        """Return True when *plaintext* matches the stored hash.

        Args:
            plaintext: The raw password supplied during login.

        Returns:
            True if the password is correct, False otherwise.
        """
        return bcrypt.checkpw(
            plaintext.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"


class AuditLog(db.Model):
    """Immutable record of every login attempt.

    Stores the outcome (success / failure) but never the raw password.
    """

    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)   # supports IPv6
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        status = "OK" if self.success else "FAIL"
        return (
            f"<AuditLog id={self.id} user={self.username!r} "
            f"status={status} ts={self.timestamp.isoformat()}>"
        )
