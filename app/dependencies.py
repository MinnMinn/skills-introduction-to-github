"""
FastAPI dependency-injection helpers.

* ``get_current_user``  — validates the Bearer JWT and returns the user record.
* ``get_redis``         — yields a Redis client (can be swapped in tests via
                          app.dependency_overrides).
"""
from __future__ import annotations

import logging
from typing import Generator

import redis as redis_lib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

from app import config, database

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

_redis_client: redis_lib.Redis | None = None


def get_redis() -> Generator[redis_lib.Redis, None, None]:
    """Yield a Redis client.  Override in tests with ``fakeredis``."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(
            config.REDIS_URL, decode_responses=True
        )
    yield _redis_client


# ---------------------------------------------------------------------------
# JWT / current-user
# ---------------------------------------------------------------------------

def _decode_token(token: str) -> dict:
    """Decode and validate a JWT, raising 401 on any failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id}
    except JWTError:
        raise credentials_exception


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """
    Dependency that validates the Bearer JWT and returns the matching user.

    Raises HTTP 401 if the token is missing, malformed, or the user no longer
    exists in the store.
    """
    token_data = _decode_token(credentials.credentials)
    user = database.get_user_by_id(token_data["user_id"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
