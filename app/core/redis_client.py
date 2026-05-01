"""Redis connection factory.

A module-level `redis_client` is created on import.
Tests can replace it by calling `set_redis_client(fake)`.
"""
import redis as _redis

from app.core.config import settings

_client: _redis.Redis | None = None


def get_redis_client() -> _redis.Redis:
    """Return the current Redis client (lazy-initialised)."""
    global _client
    if _client is None:
        _client = _redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def set_redis_client(client: _redis.Redis) -> None:  # pragma: no cover
    """Override the Redis client (used in tests with fakeredis)."""
    global _client
    _client = client
