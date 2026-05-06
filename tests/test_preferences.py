"""Tests for GET /preferences/{user_id} and PATCH /preferences/{user_id}."""
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GET endpoint
# ---------------------------------------------------------------------------

class TestGetPreferences:
    def test_get_returns_404_when_not_found(self, client: TestClient):
        response = client.get("/preferences/999")
        assert response.status_code == 404

    def test_get_returns_preferences_with_avatar_url_none_by_default(self, client: TestClient):
        """After creating a record via PATCH, avatar_url should default to None."""
        # Seed a row via PATCH (no avatar_url supplied).
        client.patch("/preferences/1", json={"theme": "dark"})

        response = client.get("/preferences/1")
        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] is None

    def test_get_returns_avatar_url_when_set(self, client: TestClient):
        url = "https://example.com/avatar.png"
        client.patch("/preferences/2", json={"avatar_url": url})

        response = client.get("/preferences/2")
        assert response.status_code == 200
        assert response.json()["avatar_url"] == url

    def test_get_response_does_not_contain_timezone(self, client: TestClient):
        """timezone field must NOT appear in the response (removed per KAN-8)."""
        client.patch("/preferences/3", json={"theme": "light"})
        data = client.get("/preferences/3").json()
        assert "timezone" not in data

    def test_get_response_contains_expected_fields(self, client: TestClient):
        client.patch("/preferences/4", json={"theme": "dark", "language": "fr"})
        data = client.get("/preferences/4").json()
        expected_fields = {"user_id", "theme", "language", "notifications", "avatar_url"}
        assert set(data.keys()) == expected_fields


# ---------------------------------------------------------------------------
# PATCH endpoint
# ---------------------------------------------------------------------------

class TestUpdatePreferences:
    def test_patch_creates_row_when_not_exists(self, client: TestClient):
        response = client.patch("/preferences/10", json={"theme": "dark"})
        assert response.status_code == 200
        assert response.json()["theme"] == "dark"

    def test_patch_with_valid_avatar_url_succeeds(self, client: TestClient):
        url = "https://cdn.example.com/images/avatar.jpg"
        response = client.patch("/preferences/11", json={"avatar_url": url})
        assert response.status_code == 200
        assert response.json()["avatar_url"] == url

    def test_patch_with_invalid_avatar_url_returns_422(self, client: TestClient):
        response = client.patch("/preferences/12", json={"avatar_url": "not-a-url"})
        assert response.status_code == 422

    def test_patch_with_non_http_url_returns_422(self, client: TestClient):
        """ftp:// URLs must not be accepted."""
        response = client.patch("/preferences/13", json={"avatar_url": "ftp://files.example.com/avatar.png"})
        assert response.status_code == 422

    def test_patch_with_avatar_url_none_clears_value(self, client: TestClient):
        url = "https://example.com/avatar.png"
        client.patch("/preferences/14", json={"avatar_url": url})
        # Explicitly clear it
        response = client.patch("/preferences/14", json={"avatar_url": None})
        assert response.status_code == 200
        assert response.json()["avatar_url"] is None

    def test_patch_partial_update_preserves_other_fields(self, client: TestClient):
        client.patch("/preferences/15", json={"theme": "dark", "language": "de"})
        # Only update notifications — other fields must remain
        response = client.patch("/preferences/15", json={"notifications": False})
        data = response.json()
        assert data["theme"] == "dark"
        assert data["language"] == "de"
        assert data["notifications"] is False
