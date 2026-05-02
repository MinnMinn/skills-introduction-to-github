"""
Unit tests for app.audit — structured audit log entries.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

import pytest

os.environ.setdefault("JWT_SECRET", "c" * 64)

from app.audit import emit_login_audit  # noqa: E402


class TestAuditLog:
    def _capture_audit(self, caplog, **kwargs):
        with caplog.at_level(logging.INFO, logger="audit.login"):
            emit_login_audit(**kwargs)
        return [r for r in caplog.records if r.name == "audit.login"]

    def test_emits_log_record(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="success",
            email="test@example.com",
            source_ip="1.2.3.4",
            http_status=200,
        )
        assert len(records) == 1

    def test_log_is_valid_json(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="failure",
            email="test@example.com",
            source_ip="1.2.3.4",
            http_status=401,
        )
        entry = json.loads(records[0].message)
        assert isinstance(entry, dict)

    def test_log_contains_required_fields(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="success",
            email="test@example.com",
            source_ip="10.0.0.1",
            http_status=200,
        )
        entry = json.loads(records[0].message)
        assert "timestamp" in entry
        assert "outcome" in entry
        assert "email_sha256" in entry
        assert "source_ip" in entry
        assert "http_status" in entry

    def test_email_is_hashed_not_plaintext(self, caplog):
        email = "private@example.com"
        records = self._capture_audit(
            caplog,
            outcome="failure",
            email=email,
            source_ip="1.2.3.4",
            http_status=401,
        )
        entry = json.loads(records[0].message)
        # The plaintext email must NOT appear in the log.
        assert email not in records[0].message
        # The SHA-256 hash should appear instead.
        expected_hash = hashlib.sha256(email.encode()).hexdigest()
        assert entry["email_sha256"] == expected_hash

    def test_outcome_success(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="success",
            email="u@example.com",
            source_ip="1.1.1.1",
            http_status=200,
        )
        entry = json.loads(records[0].message)
        assert entry["outcome"] == "success"

    def test_outcome_failure(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="failure",
            email="u@example.com",
            source_ip="1.1.1.1",
            http_status=401,
        )
        entry = json.loads(records[0].message)
        assert entry["outcome"] == "failure"

    def test_http_status_captured(self, caplog):
        records = self._capture_audit(
            caplog,
            outcome="failure",
            email="u@example.com",
            source_ip="1.1.1.1",
            http_status=429,
        )
        entry = json.loads(records[0].message)
        assert entry["http_status"] == 429
