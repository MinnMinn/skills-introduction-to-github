"""
Shared pytest fixtures.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import fakeredis
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app import config, database
from app.dependencies import get_redis
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jwt(user_id: str, secret: str = config.JWT_SECRET_KEY) -> str:
    """Create a signed JWT for *user_id*."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, secret, algorithm=config.JWT_ALGORITHM)


def auth_headers(user_id: str) -> dict:
    return {"Authorization": f"Bearer {make_jwt(user_id)}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db():
    """Reset the in-memory user store before every test."""
    database.clear_all()
    yield
    database.clear_all()


@pytest.fixture()
def fake_redis():
    """Return a fakeredis server-backed client."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture()
def client(fake_redis):
    """
    TestClient wired with a fakeredis override so tests never touch a real
    Redis instance.
    """
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def existing_user():
    """Create and return a user in the in-memory DB."""
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = database.create_user(
        email="alice@example.com",
        hashed_password=pwd_ctx.hash("s3cr3t"),
    )
    return user
