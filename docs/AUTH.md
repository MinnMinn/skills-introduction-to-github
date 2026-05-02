# Authentication

This document describes the hypothetical authentication system used by this application, including the login flow, token lifecycle, and common error codes.

---

## Overview

The authentication system is based on a **token-based** model. Clients authenticate by submitting valid credentials to the login endpoint and receive a short-lived **access token** along with a longer-lived **refresh token**. All subsequent API requests must include the access token in the `Authorization` header.

### Login Flow

1. **Client submits credentials** — The user provides their username/email and password via the login form or API client.
2. **Server validates credentials** — The server looks up the user record and verifies the password hash.
3. **Tokens issued** — On success, the server generates and returns:
   - An **access token** (short-lived, e.g. 15 minutes)
   - A **refresh token** (long-lived, e.g. 7 days)
4. **Client stores tokens** — The client stores the tokens securely (e.g. in memory or an `HttpOnly` cookie).
5. **Authenticated requests** — For every protected API call, the client includes the access token in the request header:
   ```
   Authorization: Bearer <access_token>
   ```
6. **Session ends** — The user logs out, or the refresh token expires, requiring re-authentication.

---

## Token Lifecycle

### Access Token

| Property     | Value              |
|--------------|--------------------|
| Type         | JWT (HS256)        |
| Lifetime     | 15 minutes         |
| Storage      | Memory / HttpOnly cookie |
| Revocable    | No (stateless)     |

- Issued at login and on every successful token refresh.
- Sent with each API request in the `Authorization: Bearer` header.
- Once expired, the client **must** exchange the refresh token for a new access token.

### Refresh Token

| Property     | Value              |
|--------------|--------------------|
| Type         | Opaque token       |
| Lifetime     | 7 days             |
| Storage      | HttpOnly cookie (recommended) |
| Revocable    | Yes (stored server-side) |

- Issued only at login.
- Used exclusively against the `/auth/refresh` endpoint to obtain a new access token.
- Rotated on every use — the old refresh token is invalidated and a new one is issued.
- Immediately invalidated on logout or if a reuse attempt is detected (token rotation security).

### Token Refresh Flow

```
Client                        Server
  |                              |
  |-- POST /auth/refresh ------->|
  |   { refresh_token: "..." }   |
  |                              |-- validate refresh token
  |                              |-- invalidate old token
  |                              |-- issue new access + refresh tokens
  |<-- 200 OK ------------------|
  |   { access_token: "...",     |
  |     refresh_token: "..." }   |
```

### Logout

Calling `POST /auth/logout` invalidates the current refresh token on the server side. Any further attempts to use that refresh token will be rejected with a `401 Unauthorized` error.

---

## Error Codes

The authentication system returns standard HTTP error codes. Below are the most common ones you will encounter.

### 401 Unauthorized

Returned when the request cannot be authenticated.

| Scenario | Description |
|---|---|
| Missing token | No `Authorization` header was provided. |
| Expired access token | The access token's `exp` claim is in the past. |
| Invalid token signature | The token has been tampered with or signed with the wrong key. |
| Revoked refresh token | The refresh token has been invalidated (logout, rotation). |
| Wrong credentials | The username/password combination is incorrect at login. |

**Example response:**
```json
{
  "error": "unauthorized",
  "message": "Access token is expired or invalid.",
  "status": 401
}
```

**How to handle:** Attempt a token refresh using the refresh token. If the refresh also fails with `401`, redirect the user to the login page.

---

### 403 Forbidden

Returned when the request is authenticated but the user lacks permission for the requested resource.

| Scenario | Description |
|---|---|
| Insufficient role | The user's role (e.g. `viewer`) does not permit the action (e.g. `admin`-only endpoint). |
| Account suspended | The user account exists and credentials are valid, but the account has been suspended. |
| Resource ownership | The user is trying to access or modify a resource that belongs to another user. |

**Example response:**
```json
{
  "error": "forbidden",
  "message": "You do not have permission to perform this action.",
  "status": 403
}
```

**How to handle:** Do **not** retry — the user's credentials are valid but they are not authorised. Show the user an appropriate "access denied" message and, where applicable, offer a way to request elevated permissions.

---

### 429 Too Many Requests

Returned when a client exceeds the allowed request rate.

| Scenario | Description |
|---|---|
| Login brute-force protection | Too many failed login attempts from the same IP or for the same account within a time window. |
| Token refresh rate limit | Refresh endpoint called too frequently. |
| General API rate limit | The client has exceeded the global per-user request quota. |

**Example response:**
```json
{
  "error": "too_many_requests",
  "message": "Rate limit exceeded. Please try again later.",
  "status": 429,
  "retry_after": 60
}
```

**How to handle:** Respect the `Retry-After` response header (value in seconds) before retrying. Implement exponential back-off in automated clients to avoid immediately hitting the limit again.

---

## Summary

| Code | Meaning | Action |
|------|---------|--------|
| `401` | Not authenticated | Refresh token or redirect to login |
| `403` | Not authorised | Show access-denied message; do not retry |
| `429` | Rate limited | Wait for `Retry-After` duration; use back-off |
