"""Shared pytest fixtures."""

from datetime import datetime, timedelta, timezone
from typing import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app import redis_client as rc
from app.config import settings
from app.db import reset_db
from app.main import app


# ── JWT helpers ───────────────────────────────────────────────────────────────

def make_token(user_id: str, expired: bool = False) -> str:
    """Create a signed JWT for *user_id*."""
    now = datetime.now(tz=timezone.utc)
    delta = timedelta(minutes=-1) if expired else timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state() -> Generator:
    """Reset in-memory DB and Redis before every test."""
    reset_db()
    fake = fakeredis.FakeRedis(decode_responses=True)
    rc.set_redis(fake)
    yield
    fake.flushall()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def alice_token() -> str:
    return make_token("user-001")


@pytest.fixture()
def bob_token() -> str:
    return make_token("user-002")


@pytest.fixture()
def expired_token() -> str:
    return make_token("user-001", expired=True)
