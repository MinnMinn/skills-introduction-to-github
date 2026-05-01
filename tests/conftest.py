"""
Shared pytest fixtures for all tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from jose import jwt

import app.audit as audit
import app.redis_client as redis_client
from app.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = "user-123"
TEST_USER_EMAIL = "old@example.com"


def make_token(
    user_id: str = TEST_USER_ID,
    expired: bool = False,
    missing_sub: bool = False,
) -> str:
    """Generate a signed JWT for testing."""
    now = datetime.now(tz=timezone.utc)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(hours=1)
    payload: dict = {"exp": exp}
    if not missing_sub:
        payload["sub"] = user_id
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def auth_headers(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or make_token()}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> Generator[fakeredis.FakeRedis, None, None]:
    """Replace the real Redis client with an in-memory fake for every test."""
    r = fakeredis.FakeRedis(decode_responses=True)
    redis_client._redis_override = r
    yield r
    redis_client._redis_override = None
    r.flushall()


@pytest.fixture(autouse=True)
def seed_user() -> Generator[None, None, None]:
    """Seed the in-memory user store and clean up after each test."""
    audit.upsert_user(TEST_USER_ID, TEST_USER_EMAIL)
    yield
    audit._USERS.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)
