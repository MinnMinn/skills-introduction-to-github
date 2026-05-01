"""
Application configuration — values are read from environment variables with
sensible defaults for local development.  Never commit real secrets here.
"""
import os

# JWT
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

# Redis
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Verification code settings
VERIFICATION_CODE_TTL_SECONDS: int = 15 * 60   # 15 minutes
MAX_VERIFY_ATTEMPTS: int = 5                    # rate-limit threshold

# Audit trail: how long the OLD email stays valid for login after a change
OLD_EMAIL_VALID_DAYS: int = 30
