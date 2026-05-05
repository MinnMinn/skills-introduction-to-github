"""pytest tests for GET/PUT /api/v1/preferences/{user_id}.

Covers:
- success path (GET existing, PUT creates + updates)
- not-found (GET unknown user → 404)
- validation errors (PUT with invalid payload → 422)
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.database import get_db
from src.db.models import Base
from src.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def db_session():
    """Provide a clean in-memory SQLite session per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def client(db_session: AsyncSession):
    """AsyncClient wired to the FastAPI app with the test DB session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/preferences/{user_id}
# ---------------------------------------------------------------------------


class TestGetPreferences:
    async def test_get_existing_user_returns_200(self, client: AsyncClient):
        """After a PUT, GET must return the stored preferences."""
        user_id = "user-001"
        prefs = {"theme": "dark", "notifications": True}

        # seed data via PUT
        await client.put(f"/api/v1/preferences/{user_id}", json={"preferences": prefs})

        response = await client.get(f"/api/v1/preferences/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["preferences"] == prefs

    async def test_get_unknown_user_returns_404(self, client: AsyncClient):
        """GET for a user with no preferences must return 404."""
        response = await client.get("/api/v1/preferences/nonexistent-user")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# PUT /api/v1/preferences/{user_id}
# ---------------------------------------------------------------------------


class TestUpdatePreferences:
    async def test_put_creates_preferences_returns_200(self, client: AsyncClient):
        """PUT on a new user must create the record and return 200."""
        user_id = "user-002"
        prefs = {"language": "en", "timezone": "UTC"}

        response = await client.put(
            f"/api/v1/preferences/{user_id}", json={"preferences": prefs}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["preferences"] == prefs

    async def test_put_partial_update_preserves_existing_keys(self, client: AsyncClient):
        """PUT must merge — keys absent from the patch must remain unchanged."""
        user_id = "user-003"
        initial = {"theme": "light", "language": "fr"}
        await client.put(f"/api/v1/preferences/{user_id}", json={"preferences": initial})

        patch = {"language": "de"}  # only update 'language'
        response = await client.put(
            f"/api/v1/preferences/{user_id}", json={"preferences": patch}
        )
        assert response.status_code == 200
        data = response.json()
        # 'theme' must be preserved, 'language' must be updated
        assert data["preferences"]["theme"] == "light"
        assert data["preferences"]["language"] == "de"

    async def test_put_adds_new_key_to_existing_preferences(self, client: AsyncClient):
        """PUT must add a new key without removing other keys."""
        user_id = "user-004"
        await client.put(
            f"/api/v1/preferences/{user_id}",
            json={"preferences": {"theme": "dark"}},
        )

        response = await client.put(
            f"/api/v1/preferences/{user_id}",
            json={"preferences": {"font_size": 14}},
        )
        assert response.status_code == 200
        prefs = response.json()["preferences"]
        assert prefs["theme"] == "dark"
        assert prefs["font_size"] == 14


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors:
    async def test_put_missing_preferences_key_returns_422(self, client: AsyncClient):
        """PUT without the 'preferences' field must return 422."""
        response = await client.put(
            "/api/v1/preferences/user-005", json={"wrong_field": {}}
        )
        assert response.status_code == 422

    async def test_put_preferences_not_an_object_returns_422(self, client: AsyncClient):
        """PUT where 'preferences' is not a JSON object must return 422."""
        response = await client.put(
            "/api/v1/preferences/user-006", json={"preferences": "not-an-object"}
        )
        assert response.status_code == 422

    async def test_put_empty_body_returns_422(self, client: AsyncClient):
        """PUT with an empty body must return 422."""
        response = await client.put(
            "/api/v1/preferences/user-007", content=b"", headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
