"""
Application configuration loaded from environment variables.
Never hardcode secrets — use a .env file or your deployment secret manager.
"""
import os

# JWT
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")

# Redis
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Email-change verification
VERIFICATION_CODE_TTL_SECONDS: int = int(
    os.environ.get("VERIFICATION_CODE_TTL_SECONDS", 15 * 60)  # 15 minutes
)
MAX_CONFIRM_ATTEMPTS: int = int(os.environ.get("MAX_CONFIRM_ATTEMPTS", 5))
OLD_EMAIL_GRACE_DAYS: int = int(os.environ.get("OLD_EMAIL_GRACE_DAYS", 30))
