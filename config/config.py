"""
Application configuration — structs and loaders.

Equivalent of config/config.go in the standard Go layout.

Reads configuration from environment variables with sensible defaults.
All other packages import from here; nothing reads ``os.environ`` directly.

Usage:
    from config.config import get_settings

    settings = get_settings()
    print(settings.app_host, settings.app_port)

Environment variables:
    APP_HOST        Bind host for the HTTP server         (default: "0.0.0.0")
    APP_PORT        Bind port for the HTTP server         (default: 8000)
    APP_ENV         Runtime environment name              (default: "development")
    LOG_LEVEL       Logging level (DEBUG/INFO/WARNING…)   (default: "INFO")
    LOG_FORMAT      Log output format: "text" or "json"   (default: "text")
    DATABASE_URL    Connection string for the DB           (default: "")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from the environment."""

    # HTTP server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_env: str = "development"

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"

    # Database
    database_url: str = ""

    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in the development environment."""
        return self.app_env.lower() == "development"


def _load_settings() -> Settings:
    """Read settings from environment variables."""
    return Settings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "text"),
        database_url=os.getenv("DATABASE_URL", ""),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return _load_settings()
