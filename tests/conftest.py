"""
Shared pytest fixtures.

Uses fakeredis for Redis and an in-memory SQLite database so no real
infrastructure is needed during unit tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import fakeredis

from app.main import app
from app.dependencies import get_db, get_redis
from app.models import Base, User


# ---------------------------------------------------------------------------
# In-memory SQLite database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"
_test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
_TestSessionLocal = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test; drop them after."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def db_session() -> Session:
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def registered_user(db_session: Session) -> User:
    """Insert a test user and return the ORM object."""
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    user = User(email="user@example.com", password_hash=ph.hash("OldPassword1"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Fake Redis
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_redis():
    """Return a fakeredis instance that is wiped for each test."""
    r = fakeredis.FakeRedis(decode_responses=True)
    yield r
    r.flushall()


# ---------------------------------------------------------------------------
# TestClient with dependency overrides
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session: Session, fake_redis):
    """TestClient with DB and Redis overridden to in-memory fakes."""

    def override_db():
        yield db_session

    def override_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
