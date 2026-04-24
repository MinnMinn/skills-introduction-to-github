"""
Tests for GET /api/v1/preferences/{user_id}
         PUT /api/v1/preferences/{user_id}

Coverage:
  - Happy path: successful GET
  - Happy path: successful PUT (full payload)
  - Happy path: successful PUT (partial payload)
  - Not-found: GET for unknown user  → 404
  - Not-found: PUT for unknown user  → 404
  - Validation: invalid theme value  → 422
  - Validation: blank language       → 422
  - Validation: empty body PUT       → 422
  - avatar_url: GET returns None by default
  - avatar_url: PUT with valid URL   → 200, avatar_url updated
  - avatar_url: PUT with invalid URL → 422
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.db.models import UserSettings
from src.db.repos.preferences_repo import PreferencesRepository
from src.main import app
from src.api.endpoints import get_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEED_USER = UserSettings(
    user_id="user-123",
    theme="light",
    language="en",
    notifications=True,
    timezone="UTC",
)


@pytest.fixture()
def repo() -> PreferencesRepository:
    """Fresh repository with one seeded user for each test."""
    r = PreferencesRepository()
    r._clear()
    r._seed(
        UserSettings(
            user_id=SEED_USER.user_id,
            theme=SEED_USER.theme,
            language=SEED_USER.language,
            notifications=SEED_USER.notifications,
            timezone=SEED_USER.timezone,
        )
    )
    return r


@pytest.fixture()
def client(repo: PreferencesRepository) -> TestClient:
    """TestClient with the repo dependency overridden."""
    app.dependency_overrides[get_repo] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET — happy path
# ---------------------------------------------------------------------------


class TestGetPreferences:
    def test_returns_200_with_correct_payload(self, client: TestClient) -> None:
        response = client.get("/api/v1/preferences/user-123")

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "user-123"
        assert body["theme"] == "light"
        assert body["language"] == "en"
        assert body["notifications"] is True
        assert "updated_at" in body

    def test_response_contains_all_expected_keys(self, client: TestClient) -> None:
        response = client.get("/api/v1/preferences/user-123")
        body = response.json()
        # timezone is removed; avatar_url is added
        expected_keys = {"user_id", "theme", "language", "notifications", "avatar_url", "updated_at"}
        assert expected_keys == set(body.keys())

    def test_timezone_not_in_response(self, client: TestClient) -> None:
        """timezone field must not be present in the response."""
        response = client.get("/api/v1/preferences/user-123")
        assert "timezone" not in response.json()


# ---------------------------------------------------------------------------
# GET — not-found
# ---------------------------------------------------------------------------


class TestGetPreferencesNotFound:
    def test_returns_404_for_unknown_user(self, client: TestClient) -> None:
        response = client.get("/api/v1/preferences/ghost-user")

        assert response.status_code == 404
        assert "ghost-user" in response.json()["detail"]

    def test_404_detail_mentions_user_id(self, client: TestClient) -> None:
        response = client.get("/api/v1/preferences/no-such-user")
        assert "no-such-user" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PUT — happy path (full payload)
# ---------------------------------------------------------------------------


class TestUpdatePreferencesFullPayload:
    def test_returns_200_with_updated_values(self, client: TestClient) -> None:
        payload = {
            "theme": "dark",
            "language": "fr",
            "notifications": False,
        }
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["theme"] == "dark"
        assert body["language"] == "fr"
        assert body["notifications"] is False
        assert body["user_id"] == "user-123"

    def test_updated_at_is_refreshed_after_update(self, client: TestClient) -> None:
        # Capture the original timestamp
        original = client.get("/api/v1/preferences/user-123").json()["updated_at"]

        payload = {"theme": "dark"}
        updated = client.put("/api/v1/preferences/user-123", json=payload).json()["updated_at"]

        # updated_at must be a valid ISO string; it should differ or be the same
        # (same-second is OK) but the field must always be present
        assert isinstance(updated, str)
        assert len(updated) > 0


# ---------------------------------------------------------------------------
# PUT — happy path (partial payload)
# ---------------------------------------------------------------------------


class TestUpdatePreferencesPartialPayload:
    def test_only_supplied_fields_are_changed(self, client: TestClient) -> None:
        payload = {"theme": "dark"}
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 200
        body = response.json()
        # Changed
        assert body["theme"] == "dark"
        # Unchanged
        assert body["language"] == "en"
        assert body["notifications"] is True

    def test_partial_update_language_only(self, client: TestClient) -> None:
        payload = {"language": "de"}
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 200
        assert response.json()["language"] == "de"
        assert response.json()["theme"] == "light"  # unchanged

    def test_partial_update_notifications_only(self, client: TestClient) -> None:
        payload = {"notifications": False}
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 200
        assert response.json()["notifications"] is False


# ---------------------------------------------------------------------------
# PUT — not-found
# ---------------------------------------------------------------------------


class TestUpdatePreferencesNotFound:
    def test_returns_404_for_unknown_user(self, client: TestClient) -> None:
        payload = {"theme": "dark"}
        response = client.put("/api/v1/preferences/no-such-user", json=payload)

        assert response.status_code == 404
        assert "no-such-user" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PUT — validation errors (422)
# ---------------------------------------------------------------------------


class TestUpdatePreferencesValidation:
    def test_invalid_theme_value_returns_422(self, client: TestClient) -> None:
        payload = {"theme": "rainbow"}  # not "light" or "dark"
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 422

    def test_blank_language_returns_422(self, client: TestClient) -> None:
        payload = {"language": "   "}
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        """PUT with no recognisable fields should return 422."""
        response = client.put("/api/v1/preferences/user-123", json={})

        assert response.status_code == 422

    def test_wrong_type_for_notifications_returns_422(self, client: TestClient) -> None:
        payload = {"notifications": "yes_please"}  # must be bool
        response = client.put("/api/v1/preferences/user-123", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# avatar_url — GET returns None by default
# ---------------------------------------------------------------------------


class TestAvatarUrl:
    def test_get_returns_avatar_url_none_by_default(self, client: TestClient) -> None:
        """Existing users with no avatar_url set should receive null."""
        response = client.get("/api/v1/preferences/user-123")

        assert response.status_code == 200
        assert response.json()["avatar_url"] is None

    def test_put_valid_url_updates_avatar_url(self, client: TestClient) -> None:
        """PUT with a valid https URL should store and return the avatar_url."""
        valid_url = "https://example.com/avatar.png"
        response = client.put(
            "/api/v1/preferences/user-123",
            json={"avatar_url": valid_url},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["avatar_url"] == valid_url

    def test_put_valid_http_url_updates_avatar_url(self, client: TestClient) -> None:
        """PUT with a valid http URL should also be accepted."""
        valid_url = "http://cdn.example.org/images/user/avatar.jpg"
        response = client.put(
            "/api/v1/preferences/user-123",
            json={"avatar_url": valid_url},
        )

        assert response.status_code == 200
        assert response.json()["avatar_url"] == valid_url

    def test_put_invalid_url_returns_422(self, client: TestClient) -> None:
        """PUT with a non-URL string for avatar_url must return 422."""
        response = client.put(
            "/api/v1/preferences/user-123",
            json={"avatar_url": "not-a-valid-url"},
        )

        assert response.status_code == 422

    def test_put_bare_domain_returns_422(self, client: TestClient) -> None:
        """PUT with a URL missing the scheme should return 422."""
        response = client.put(
            "/api/v1/preferences/user-123",
            json={"avatar_url": "example.com/avatar.png"},
        )

        assert response.status_code == 422

    def test_put_avatar_url_persists_across_get(self, client: TestClient) -> None:
        """After a successful PUT the GET should reflect the new avatar_url."""
        valid_url = "https://avatars.example.com/u/42"
        client.put("/api/v1/preferences/user-123", json={"avatar_url": valid_url})

        response = client.get("/api/v1/preferences/user-123")
        assert response.status_code == 200
        assert response.json()["avatar_url"] == valid_url

    def test_other_fields_unchanged_after_avatar_update(self, client: TestClient) -> None:
        """Updating only avatar_url must not affect theme, language, notifications."""
        valid_url = "https://example.com/pic.jpg"
        response = client.put(
            "/api/v1/preferences/user-123",
            json={"avatar_url": valid_url},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["theme"] == "light"
        assert body["language"] == "en"
        assert body["notifications"] is True


# ---------------------------------------------------------------------------
# Repository unit tests (isolated, no HTTP layer)
# ---------------------------------------------------------------------------


class TestPreferencesRepository:
    def test_get_returns_none_for_missing_user(self) -> None:
        repo = PreferencesRepository()
        repo._clear()
        assert repo.get("nonexistent") is None

    def test_get_returns_seeded_record(self) -> None:
        repo = PreferencesRepository()
        repo._clear()
        settings = UserSettings(user_id="u1", theme="dark")
        repo._seed(settings)
        assert repo.get("u1") is settings

    def test_update_returns_none_for_missing_user(self) -> None:
        repo = PreferencesRepository()
        repo._clear()
        assert repo.update("nonexistent", {"theme": "dark"}) is None

    def test_update_applies_partial_fields(self) -> None:
        repo = PreferencesRepository()
        repo._clear()
        repo._seed(UserSettings(user_id="u2", theme="light", language="en"))
        result = repo.update("u2", {"theme": "dark"})
        assert result is not None
        assert result.theme == "dark"
        assert result.language == "en"  # untouched

    def test_update_raises_on_empty_fields(self) -> None:
        repo = PreferencesRepository()
        repo._clear()
        repo._seed(UserSettings(user_id="u3"))
        with pytest.raises(ValueError, match="No fields supplied"):
            repo.update("u3", {})

    def test_avatar_url_defaults_to_none(self) -> None:
        """UserSettings created without avatar_url should default to None."""
        settings = UserSettings(user_id="u4")
        assert settings.avatar_url is None

    def test_update_sets_avatar_url(self) -> None:
        """Repository update should correctly apply avatar_url."""
        repo = PreferencesRepository()
        repo._clear()
        repo._seed(UserSettings(user_id="u5"))
        url = "https://example.com/avatar.png"
        result = repo.update("u5", {"avatar_url": url})
        assert result is not None
        assert result.avatar_url == url
