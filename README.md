# skills-introduction-to-github

## Login Endpoint

A secure `POST /login` Flask endpoint (`login.py`) that authenticates users and returns session tokens.

### Quick Start

```bash
pip install -r requirements.txt
python login.py          # starts Flask on http://127.0.0.1:5000
```

### Usage

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"supersecret"}'
# → {"token": "<64-char hex string>"}
```

### Running Tests

```bash
pip install pytest
pytest test_login.py -v
```

### Security Features

| Feature | Detail |
|---|---|
| Password hashing | argon2id (t=3, m=65536, p=1, hash_len=32, salt_len=16) |
| Session tokens | `secrets.token_hex(32)` (CSPRNG) |
| User enumeration prevention | Dummy verify against fixed hash for unknown emails |
| Rate limiting | 10 req/IP/60 s · 5 failures/email/60 s → HTTP 429 + Retry-After |
| Cookie attributes | Secure; HttpOnly; SameSite=Lax; Path=/ |
| Error handling | Generic `{"error":"internal_error"}` on exceptions – no stack traces |
| Log redaction | `password` field redacted before any log write |
