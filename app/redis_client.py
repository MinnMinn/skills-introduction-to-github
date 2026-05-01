"""
Redis client factory with a module-level override hook for testing.

Usage in tests:
    import app.redis_client as rc
    rc._redis_override = fakeredis.FakeRedis()
"""
from __future__ import annotations

import redis as _redis_lib

from app.config import REDIS_URL

# Set this in tests to inject a fake Redis instance without monkeypatching the
# entire module.
_redis_override: _redis_lib.Redis | None = None


def get_redis() -> _redis_lib.Redis:
    """Return the active Redis client (real or injected override)."""
    if _redis_override is not None:
        return _redis_override
    return _redis_lib.from_url(REDIS_URL, decode_responses=True)
