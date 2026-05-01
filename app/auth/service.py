"""Business logic for the /login flow.

Responsibilities:
  - Look up the user by username
  - Validate the supplied password with bcrypt
  - Issue a signed JWT on success
  - Write an AuditLog row for every attempt (success and failure)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from ..extensions import db
from ..models import AuditLog, User


def _write_audit(username: str, success: bool, ip_address: Optional[str]) -> None:
    """Persist a single audit-log entry.

    Args:
        username:   The username supplied in the login request.
        success:    True if authentication succeeded, False otherwise.
        ip_address: Remote address of the caller (may be None).
    """
    entry = AuditLog(
        username=username,
        success=success,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    db.session.add(entry)
    db.session.commit()


def attempt_login(
    username: str,
    password: str,
    ip_address: Optional[str],
    secret_key: str,
    algorithm: str = "HS256",
    expiry_seconds: int = 3600,
) -> Optional[str]:
    """Try to authenticate a user and return a JWT on success.

    The audit log is written regardless of outcome.

    Args:
        username:       Username from the request body.
        password:       Plaintext password from the request body.
        ip_address:     Remote address of the caller.
        secret_key:     Application secret used to sign the JWT.
        algorithm:      JWT signing algorithm (default HS256).
        expiry_seconds: Token lifetime in seconds (default 3600).

    Returns:
        A signed JWT string on success, or None if authentication failed.
    """
    user: Optional[User] = User.query.filter_by(username=username).first()

    authenticated = user is not None and user.check_password(password)

    _write_audit(username=username, success=authenticated, ip_address=ip_address)

    if not authenticated:
        return None

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "iat": now,
        "exp": now + timedelta(seconds=expiry_seconds),
    }
    token: str = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token
