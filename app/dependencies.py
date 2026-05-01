"""
FastAPI dependency providers for Redis and the database session.
"""
from __future__ import annotations

from collections.abc import Generator

import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

_redis_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    """Return a module-level Redis client (lazily created).

    Security rule 13: connection string is read from the environment variable
    REDIS_URL — never hardcoded.  Redis MUST be configured with authentication
    and MUST NOT bind to a public network interface.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
    return _redis_client


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and guarantee it is closed afterwards."""
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
