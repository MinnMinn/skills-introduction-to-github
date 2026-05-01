"""Application settings loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Verification
    EMAIL_VERIFICATION_TTL_SECONDS: int = 900  # 15 minutes
    EMAIL_CHANGE_MAX_ATTEMPTS: int = 5

    # Audit
    OLD_EMAIL_RETENTION_DAYS: int = 30


settings = Settings()
