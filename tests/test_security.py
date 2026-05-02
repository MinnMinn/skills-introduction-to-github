"""
Unit tests for app.security — password hashing and JWT creation.
"""
from __future__ import annotations

import os
import time

import pytest
from jose import jwt

os.environ.setdefault("JWT_SECRET", "b" * 64)

from app.security import hash_password, verify_password, create_access_token  # noqa: E402


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("secret")
        assert h != "secret"

    def test_hash_starts_with_argon2id(self):
        h = hash_password("secret")
        assert "$argon2id$" in h

    def test_verify_correct_password(self):
        h = hash_password("correct_horse")
        assert verify_password("correct_horse", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct_horse")
        assert verify_password("wrong_horse", h) is False

    def test_verify_empty_password(self):
        h = hash_password("non_empty")
        assert verify_password("", h) is False

    def test_verify_invalid_hash(self):
        assert verify_password("anything", "not_a_valid_hash") is False

    def test_two_hashes_of_same_password_differ(self):
        """Argon2 uses random salts — two hashes of the same password differ."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestJWTCreation:
    def test_token_is_string(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)

    def test_token_contains_sub(self):
        secret = os.environ["JWT_SECRET"]
        token = create_access_token("user-abc")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "user-abc"

    def test_token_contains_exp(self):
        secret = os.environ["JWT_SECRET"]
        token = create_access_token("user-abc")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert "exp" in payload

    def test_token_exp_is_at_most_3600_seconds(self):
        secret = os.environ["JWT_SECRET"]
        now = int(time.time())
        token = create_access_token("user-abc")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["exp"] <= now + 3600 + 2  # +2 s for clock drift in tests

    def test_token_only_has_sub_and_exp(self):
        secret = os.environ["JWT_SECRET"]
        token = create_access_token("user-xyz")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert set(payload.keys()) == {"sub", "exp"}

    def test_token_is_hs256_signed(self):
        """The header must declare HS256 algorithm."""
        header = jwt.get_unverified_header(create_access_token("u"))
        assert header["alg"] == "HS256"

    def test_tampered_token_rejected(self):
        secret = os.environ["JWT_SECRET"]
        token = create_access_token("user-abc")
        parts = token.split(".")
        # Corrupt the signature
        parts[2] = parts[2][:-4] + "XXXX"
        bad_token = ".".join(parts)
        with pytest.raises(Exception):
            jwt.decode(bad_token, secret, algorithms=["HS256"])
