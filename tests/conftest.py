"""
Shared pytest fixtures.

- Wires in fakeredis so tests never need a real Redis.
- Creates an in-memory user for auth tests.
- Provides a TestClient with a valid Authorization header.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

import fakeredis
from fastapi.testclient import TestClient
from jose import jwt

import app.db as db_module
import app.redis_client as rc
from app.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_token(user_id: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(tz=timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory DB and Redis before every test."""
    db_module.clear_all()
    fake = fakeredis.FakeRedis(decode_responses=True)
    rc.set_redis(fake)
    yield
    db_module.clear_all()
    fake.flushall()


@pytest.fixture()
def user() -> dict:
    """A persisted user record."""
    return db_module.create_user(
        email="original@example.com",
        hashed_password="hashed_pw",
    )


@pytest.fixture()
def auth_headers(user: dict) -> dict:
    token = make_token(user["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
