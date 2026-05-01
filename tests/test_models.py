"""Unit tests for the User and AuditLog models."""
import pytest

from app.models import AuditLog, User


class TestUserModel:
    def test_set_password_stores_hash(self, db):
        """Raw password must not appear in the stored hash."""
        user = User(username="bob")
        user.set_password("secret123")
        assert user.password_hash != "secret123"
        assert user.password_hash  # not empty

    def test_check_password_correct(self, db):
        """check_password returns True for the correct plaintext."""
        user = User(username="carol")
        user.set_password("my-password")
        assert user.check_password("my-password") is True

    def test_check_password_wrong(self, db):
        """check_password returns False for an incorrect plaintext."""
        user = User(username="dave")
        user.set_password("my-password")
        assert user.check_password("wrong-password") is False

    def test_check_password_empty(self, db):
        """check_password returns False for an empty string."""
        user = User(username="eve")
        user.set_password("my-password")
        assert user.check_password("") is False

    def test_unique_username_constraint(self, db):
        """Inserting two users with the same username must raise an error."""
        from sqlalchemy.exc import IntegrityError

        u1 = User(username="duplicate")
        u1.set_password("pass1")
        db.session.add(u1)
        db.session.commit()

        u2 = User(username="duplicate")
        u2.set_password("pass2")
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_password_hashes_are_different_per_call(self, db):
        """bcrypt salt is re-generated on each set_password call."""
        u1 = User(username="frank1")
        u1.set_password("same-password")
        u2 = User(username="frank2")
        u2.set_password("same-password")
        assert u1.password_hash != u2.password_hash


class TestAuditLogModel:
    def test_audit_log_persists(self, db):
        """AuditLog rows should be persisted and retrievable."""
        from datetime import datetime, timezone

        entry = AuditLog(
            username="grace",
            success=True,
            ip_address="127.0.0.1",
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()

        fetched = AuditLog.query.filter_by(username="grace").first()
        assert fetched is not None
        assert fetched.success is True
        assert fetched.ip_address == "127.0.0.1"

    def test_audit_log_failure_entry(self, db):
        """AuditLog can store failed login attempts."""
        from datetime import datetime, timezone

        entry = AuditLog(
            username="heidi",
            success=False,
            ip_address="10.0.0.1",
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()

        fetched = AuditLog.query.filter_by(username="heidi").first()
        assert fetched.success is False
