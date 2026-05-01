"""Unit tests for the auth service layer."""
import jwt

from app.auth.service import attempt_login
from app.models import AuditLog, User


SECRET = "unit-test-secret"
ALGORITHM = "HS256"


class TestAttemptLogin:
    def test_returns_jwt_on_valid_credentials(self, app, existing_user):
        """A valid username/password pair should return a signed JWT."""
        with app.app_context():
            token = attempt_login(
                username="alice",
                password="correct-horse-battery-staple",
                ip_address="127.0.0.1",
                secret_key=app.config["SECRET_KEY"],
                algorithm=app.config["JWT_ALGORITHM"],
            )
            assert token is not None
            payload = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=[app.config["JWT_ALGORITHM"]],
            )
            assert payload["username"] == "alice"
            assert "exp" in payload
            assert "iat" in payload
            assert "sub" in payload

    def test_returns_none_on_wrong_password(self, app, existing_user):
        """Wrong password must return None."""
        with app.app_context():
            token = attempt_login(
                username="alice",
                password="wrong-password",
                ip_address="127.0.0.1",
                secret_key=app.config["SECRET_KEY"],
            )
            assert token is None

    def test_returns_none_for_unknown_user(self, app, db):
        """Non-existent username must return None."""
        with app.app_context():
            token = attempt_login(
                username="nobody",
                password="any-password",
                ip_address="127.0.0.1",
                secret_key=app.config["SECRET_KEY"],
            )
            assert token is None

    def test_audit_log_written_on_success(self, app, existing_user):
        """A successful login must produce an AuditLog row with success=True."""
        with app.app_context():
            attempt_login(
                username="alice",
                password="correct-horse-battery-staple",
                ip_address="192.168.1.1",
                secret_key=app.config["SECRET_KEY"],
            )
            log = AuditLog.query.filter_by(username="alice", success=True).first()
            assert log is not None
            assert log.ip_address == "192.168.1.1"

    def test_audit_log_written_on_failure(self, app, existing_user):
        """A failed login must produce an AuditLog row with success=False."""
        with app.app_context():
            attempt_login(
                username="alice",
                password="bad-password",
                ip_address="192.168.1.2",
                secret_key=app.config["SECRET_KEY"],
            )
            log = AuditLog.query.filter_by(username="alice", success=False).first()
            assert log is not None
            assert log.ip_address == "192.168.1.2"

    def test_audit_log_written_for_unknown_user(self, app, db):
        """Even if the user doesn't exist an audit entry must be written."""
        with app.app_context():
            attempt_login(
                username="ghost",
                password="any",
                ip_address="10.0.0.5",
                secret_key=app.config["SECRET_KEY"],
            )
            log = AuditLog.query.filter_by(username="ghost", success=False).first()
            assert log is not None

    def test_jwt_expiry_is_set(self, app, existing_user):
        """The JWT 'exp' claim must be in the future."""
        from datetime import datetime, timezone

        with app.app_context():
            token = attempt_login(
                username="alice",
                password="correct-horse-battery-staple",
                ip_address="127.0.0.1",
                secret_key=app.config["SECRET_KEY"],
                expiry_seconds=60,
            )
            payload = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=[app.config["JWT_ALGORITHM"]],
            )
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            assert exp > datetime.now(timezone.utc)
