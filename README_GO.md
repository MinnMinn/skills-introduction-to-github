# User Preferences API — Go

This directory contains the **Golang migration** of the original Python/FastAPI application (see KAN-10).

## Project structure

```
cmd/
  server/
    main.go          ← entry-point; wires router + repos + handlers
    main_test.go     ← integration test for /health

internal/
  models/
    models.go        ← domain structs (UserSettings, Order)
  repository/
    preferences_repo.go       ← in-memory PreferencesRepository
    preferences_repo_test.go  ← unit tests
    orders_repo.go            ← in-memory OrdersRepository
    orders_repo_test.go       ← unit tests
  handlers/
    helpers.go           ← shared JSON writing helpers & error shapes
    preferences.go       ← GET + PUT /api/v1/preferences/{user_id}
    preferences_test.go  ← handler tests
    orders.go            ← POST /api/v1/orders
    orders_test.go       ← handler tests
```

## Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe → `{"status":"ok"}` |
| `GET`  | `/api/v1/preferences/{user_id}` | Return user preferences |
| `PUT`  | `/api/v1/preferences/{user_id}` | Partial update of preferences |
| `POST` | `/api/v1/orders` | Create a new order |

## Validation (mirrors original Python rules)

**Preferences PUT**
- `theme` — must be `"light"` or `"dark"`
- `language` — must not be blank
- `timezone` — must not be blank
- `notifications` — must be a boolean
- At least one field required

**Orders POST**
- `product_id` — required; must be a valid UUID v4
- `quantity` — required; integer strictly > 0
- `price` — required; decimal string or number ≥ 0.01

## Running

```bash
go run ./cmd/server
# or
go build -o api ./cmd/server && ./api
```

The default port is **8080**. Override with `PORT=9090 ./api`.

## Testing

```bash
go test ./...
```

## Dependencies

**None** — the implementation uses the Go standard library only (`net/http`, `encoding/json`, `crypto/rand`, `sync`, etc.).
