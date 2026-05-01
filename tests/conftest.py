"""Shared pytest fixtures for the test suite."""
import pytest

from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture(scope="function")
def app():
    """Create a fresh application instance backed by an in-memory SQLite DB."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRY_SECONDS": 3600,
    }
    application = create_app(config=test_config)
    yield application


@pytest.fixture(scope="function")
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Database session bound to the test app context."""
    with app.app_context():
        yield _db


@pytest.fixture(scope="function")
def existing_user(db):
    """A User row with a known bcrypt-hashed password already in the DB."""
    user = User(username="alice")
    user.set_password("correct-horse-battery-staple")
    db.session.add(user)
    db.session.commit()
    return user
