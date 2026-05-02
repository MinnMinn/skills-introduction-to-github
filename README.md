# Login Service

A minimal FastAPI service that provides a secure `POST /api/login` endpoint.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Set required environment variables (NEVER commit real secrets)
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="sqlite:///./login_service.db"

# 3. Run the server
python run.py
# or: uvicorn app.main:app --reload
```

## API

### `POST /api/login`

Authenticate a user by email and password.

**Request body**
```json
{
  "email": "user@example.com",
  "password": "YourP@ssword1"
}
```

**Success — HTTP 200**
```json
{ "token": "<signed-HS256-JWT>" }
```
A `session` cookie (HttpOnly, Secure, SameSite=Strict, Path=/api) is also set.

**Failure — HTTP 401**
```json
{ "error": "invalid_credentials" }
```

**Validation error — HTTP 400**
```json
{
  "error": "validation_error",
  "detail": [{ "field": "body.email", "message": "...", "type": "..." }]
}
```

**Rate limited — HTTP 429**
```json
{ "error": "too_many_requests" }
```

## Security Notes

| Control | Implementation |
|---|---|
| Password hashing | Argon2id (t=3, m=65536 KiB, p=1) via argon2-cffi |
| JWT signing | HS256, secret from `JWT_SECRET` env-var only (≥ 32 bytes) |
| JWT claims | `sub` (user UUID) + `exp` only; expiry ≤ 3600 s |
| SQL injection | SQLAlchemy ORM parameterised queries |
| Rate limiting | 5 failures/email/60 s + 20 requests/IP/60 s |
| Audit logging | Structured JSON; email stored as SHA-256 hash |
| Error handling | Generic 500 body; no stack traces exposed |
| No user enumeration | Identical 401 body for unknown-email and wrong-password |

## Running Tests

```bash
JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  pytest tests/ -v --cov=app --cov-report=term-missing
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `JWT_SECRET` | **Yes** | — | ≥ 32-byte secret for JWT signing |
| `DATABASE_URL` | No | `sqlite:///./login_service.db` | SQLAlchemy DB URL |
| `JWT_EXPIRY_SECONDS` | No | `3600` | Token lifetime (max 3600) |
| `RATE_LIMIT_EMAIL_FAILURES` | No | `5` | Max failures per email per window |
| `RATE_LIMIT_IP_REQUESTS` | No | `20` | Max requests per IP per window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate-limit sliding window length |
