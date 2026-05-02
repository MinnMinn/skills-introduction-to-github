"""
Shared pytest fixtures.

The test suite uses an in-memory SQLite database and overrides FastAPI
dependencies so each test gets a clean, isolated session.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Inject test secrets BEFORE any app import so config validation passes.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "JWT_SECRET",
    # 64 hex chars = 32 bytes = 256 bits — meets the ≥ 256-bit requirement.
    "a" * 64,
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.repositories import UserRepository  # noqa: E402

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests
# ---------------------------------------------------------------------------
TEST_DB_URL = "sqlite:///:memory:"
_test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(autouse=True)
def _reset_db():
    """Recreate all tables before each test; drop them after."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def db_session():
    """Yield a test DB session."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient with the DB dependency overridden to use the
    in-memory test session.
    """

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(db_session):
    """Create and return a registered test user."""
    repo = UserRepository(db_session)
    user = repo.create(email="alice@example.com", plain_password="CorrectHorse99!")
    return user
