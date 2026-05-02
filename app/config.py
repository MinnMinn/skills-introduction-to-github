"""
Application configuration.

All secrets and environment-specific values are loaded exclusively from
environment variables (or a secrets manager injection).  No secrets are
hardcoded here or in any committed file.
"""
from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Read-only view of runtime configuration."""

    # ------------------------------------------------------------------ #
    # JWT
    # ------------------------------------------------------------------ #
    @property
    def jwt_secret(self) -> str:
        """
        HS256 signing secret — must be at least 256 random bits (32 bytes).
        Inject via JWT_SECRET environment variable or a secrets manager.
        """
        secret = os.environ.get("JWT_SECRET", "")
        if not secret:
            raise RuntimeError(
                "JWT_SECRET environment variable is required and must not be empty."
            )
        if len(secret.encode()) < 32:
            raise RuntimeError(
                "JWT_SECRET must be at least 32 bytes (256 bits) long."
            )
        return secret

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @property
    def jwt_expiry_seconds(self) -> int:
        """Token lifetime; capped at 3600 s (1 hour) per security policy."""
        raw = int(os.environ.get("JWT_EXPIRY_SECONDS", "3600"))
        return min(raw, 3600)

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    @property
    def database_url(self) -> str:
        return os.environ.get("DATABASE_URL", "sqlite:///./login_service.db")

    # ------------------------------------------------------------------ #
    # Rate limiting
    # ------------------------------------------------------------------ #
    @property
    def rate_limit_failures_per_email(self) -> int:
        """Max failed login attempts per email per window."""
        return int(os.environ.get("RATE_LIMIT_EMAIL_FAILURES", "5"))

    @property
    def rate_limit_requests_per_ip(self) -> int:
        """Max total login requests per IP per window."""
        return int(os.environ.get("RATE_LIMIT_IP_REQUESTS", "20"))

    @property
    def rate_limit_window_seconds(self) -> int:
        return int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
