"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Email-change verification
    verification_code_ttl_seconds: int = 900  # 15 minutes
    max_verify_attempts: int = 5

    # Audit trail retention
    old_email_retention_days: int = 30


settings = Settings()
