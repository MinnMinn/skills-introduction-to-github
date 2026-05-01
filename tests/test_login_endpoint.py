"""Integration tests for the POST /login endpoint."""
import json

import jwt


class TestLoginEndpoint:
    # ------------------------------------------------------------------ #
    # Happy path                                                           #
    # ------------------------------------------------------------------ #

    def test_valid_credentials_returns_200_and_token(self, client, app, existing_user):
        """POST /login with correct creds returns HTTP 200 and a valid JWT."""
        response = client.post(
            "/login",
            data=json.dumps(
                {"username": "alice", "password": "correct-horse-battery-staple"}
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        body = response.get_json()
        assert "token" in body

        # Verify the token is a well-formed, signed JWT
        payload = jwt.decode(
            body["token"],
            app.config["SECRET_KEY"],
            algorithms=[app.config["JWT_ALGORITHM"]],
        )
        assert payload["username"] == "alice"

    def test_token_contains_expected_claims(self, client, app, existing_user):
        """The returned JWT must carry sub, username, iat, exp claims."""
        response = client.post(
            "/login",
            json={"username": "alice", "password": "correct-horse-battery-staple"},
        )
        token = response.get_json()["token"]
        payload = jwt.decode(
            token,
            app.config["SECRET_KEY"],
            algorithms=[app.config["JWT_ALGORITHM"]],
        )
        for claim in ("sub", "username", "iat", "exp"):
            assert claim in payload, f"Missing JWT claim: {claim}"

    # ------------------------------------------------------------------ #
    # Invalid credentials → 401                                           #
    # ------------------------------------------------------------------ #

    def test_wrong_password_returns_401(self, client, existing_user):
        """Wrong password must yield HTTP 401."""
        response = client.post(
            "/login",
            json={"username": "alice", "password": "wrong-password"},
        )
        assert response.status_code == 401
        body = response.get_json()
        assert body["error"] == "Invalid credentials"

    def test_unknown_username_returns_401(self, client, db):
        """Non-existent username must yield HTTP 401."""
        response = client.post(
            "/login",
            json={"username": "nobody", "password": "any-password"},
        )
        assert response.status_code == 401
        body = response.get_json()
        assert body["error"] == "Invalid credentials"

    # ------------------------------------------------------------------ #
    # Bad requests → 400                                                   #
    # ------------------------------------------------------------------ #

    def test_missing_username_returns_400(self, client):
        """Request without username must yield HTTP 400."""
        response = client.post("/login", json={"password": "secret"})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_missing_password_returns_400(self, client):
        """Request without password must yield HTTP 400."""
        response = client.post("/login", json={"username": "alice"})
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_empty_body_returns_400(self, client):
        """Completely empty body must yield HTTP 400."""
        response = client.post("/login", json={})
        assert response.status_code == 400

    def test_non_json_body_returns_400(self, client):
        """Non-JSON content type must yield HTTP 400."""
        response = client.post(
            "/login",
            data="username=alice&password=secret",
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 400

    def test_whitespace_only_username_returns_400(self, client):
        """Whitespace-only username must yield HTTP 400 after stripping."""
        response = client.post(
            "/login",
            json={"username": "   ", "password": "secret"},
        )
        assert response.status_code == 400

    # ------------------------------------------------------------------ #
    # Audit log integration                                               #
    # ------------------------------------------------------------------ #

    def test_audit_log_created_on_successful_login(self, client, app, existing_user):
        """A successful login must write a success audit entry."""
        from app.models import AuditLog

        client.post(
            "/login",
            json={"username": "alice", "password": "correct-horse-battery-staple"},
        )
        with app.app_context():
            log = AuditLog.query.filter_by(username="alice", success=True).first()
            assert log is not None

    def test_audit_log_created_on_failed_login(self, client, app, existing_user):
        """A failed login must write a failure audit entry."""
        from app.models import AuditLog

        client.post(
            "/login",
            json={"username": "alice", "password": "bad"},
        )
        with app.app_context():
            log = AuditLog.query.filter_by(username="alice", success=False).first()
            assert log is not None

    def test_multiple_attempts_are_all_logged(self, client, app, existing_user):
        """Every request must produce its own AuditLog row."""
        from app.models import AuditLog

        for _ in range(3):
            client.post(
                "/login",
                json={"username": "alice", "password": "wrong"},
            )
        with app.app_context():
            count = AuditLog.query.filter_by(username="alice", success=False).count()
            assert count == 3
