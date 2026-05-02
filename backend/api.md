# Feature Submit — API Endpoint

## Overview

This document describes the `POST /api/feature/submit` endpoint that powers the feature workflow. The endpoint is called by the **Submit Button** on the frontend and returns a structured JSON response.

## Related Resources

- 🖱️ **Frontend component** — see [`../frontend/button.md`](../frontend/button.md) for the UI element that calls this endpoint.
- 📖 **End-user instructions** — see [`../docs/user-guide.md`](../docs/user-guide.md) for the user-facing description of the workflow.

---

## Endpoint Reference

### `POST /api/feature/submit`

Accepts a feature submission payload, validates it, persists it to the database, and returns a confirmation object.

#### Request

**Headers**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <token>` |

**Body**

```jsonc
{
  "title": "string",       // Required. 1–120 characters.
  "description": "string", // Optional. Max 1 000 characters.
  "tags": ["string"]       // Optional. Array of tag strings, max 10 items.
}
```

#### Responses

**`200 OK` — Success**

```json
{
  "id": "f3a1c2d4-...",
  "title": "My Feature",
  "createdAt": "2024-06-01T12:00:00Z",
  "status": "pending_review"
}
```

**`400 Bad Request` — Validation error**

```json
{
  "error": "Validation failed",
  "details": [
    { "field": "title", "message": "Title is required." }
  ]
}
```

**`401 Unauthorized`**

```json
{
  "error": "Unauthorized"
}
```

**`500 Internal Server Error`**

```json
{
  "error": "An unexpected error occurred. Please try again later."
}
```

---

## Authentication

All requests must include a valid Bearer token in the `Authorization` header. Tokens are issued by the `/api/auth/token` endpoint. Unauthenticated requests receive a `401` response.

---

## Rate Limiting

| Limit | Window |
|-------|--------|
| 30 requests | per user per minute |

When the limit is exceeded the server responds with `HTTP 429 Too Many Requests` and a `Retry-After` header indicating the number of seconds to wait.

---

## Implementation Notes

- Input is validated with JSON Schema before reaching the service layer.
- The `title` field is sanitised (HTML-escaped) before storage.
- Responses are always `application/json`.
- The [frontend Submit Button](../frontend/button.md) reads the top-level `error` field on non-`200` responses and surfaces it beneath the button.

---

## See Also

- [Frontend Button component](../frontend/button.md)
- [User Guide](../docs/user-guide.md)
