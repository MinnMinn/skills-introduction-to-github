"""Shared pytest fixtures."""
import fakeredis
import pytest
from fastapi.testclient import TestClient

import app.core.redis_client as redis_module
import app.models.user as user_module
from app.core.security import create_access_token
from app.main import app


@pytest.fixture(autouse=True)
def reset_user_store():
    """Reset the in-memory user store before every test."""
    user_module._users = {
        "u1": {
            "id": "u1",
            "email": "user@example.com",
            "hashed_password": "hashed_password_stub",
            "email_audit": [],
        }
    }
    yield
    # Cleanup (already reset at start of next test)


@pytest.fixture(autouse=True)
def fake_redis():
    """Replace the Redis client with an in-process fakeredis instance."""
    client = fakeredis.FakeRedis(decode_responses=True)
    redis_module.set_redis_client(client)
    yield client
    client.flushall()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    """Return Authorization headers for the default test user (u1)."""
    token = create_access_token(subject="u1")
    return {"Authorization": f"Bearer {token}"}
