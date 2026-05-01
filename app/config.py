"""
Application configuration — reads from environment variables with safe defaults
for local development / tests.  Never hardcode secrets in production.
"""
import os

# JWT
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "changeme-use-env-var-in-production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

# Redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Email verification
VERIFY_CODE_TTL_SECONDS: int = 15 * 60          # 15 minutes
VERIFY_CODE_MAX_ATTEMPTS: int = 5               # rate-limit threshold

# Audit trail — old email remains valid for login during this window
OLD_EMAIL_GRACE_PERIOD_DAYS: int = 30
