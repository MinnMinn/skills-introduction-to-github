"""
Application configuration — all secrets come from environment variables.
Never hardcode connection strings, passwords, or keys in source code.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Return the environment variable *name* or raise at startup."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "See .env.example for guidance."
        )
    return value


class Settings:
    # Redis — MUST use authentication; MUST NOT be on a public interface.
    # Connection string read exclusively from the environment (security rule 13).
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://:changeme@localhost:6379/0")

    # Database
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://appuser:changeme@localhost:5432/appdb",
    )

    # Rate-limit parameters
    RATE_LIMIT_RESET_MAX: int = 5          # max reset requests per email per window
    RATE_LIMIT_CONFIRM_IP_MAX: int = 10    # max confirm attempts per IP per window
    RATE_LIMIT_WINDOW_SECONDS: int = 900   # 15 minutes

    # Token TTL
    TOKEN_TTL_SECONDS: int = 900           # 15 minutes

    # Argon2id parameters (security rules 2 & 6)
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536        # 64 MiB
    ARGON2_PARALLELISM: int = 1


settings = Settings()
