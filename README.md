# User Preferences API

A dual-implementation REST API for managing per-user application preferences and orders, written in both **Python (FastAPI)** and **Go (standard library)**. This repository serves as a practical introduction to GitHub workflows — branching, pull requests, code review, and collaboration.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Go 1.22+](https://img.shields.io/badge/Go-1.22%2B-00ADD8?logo=go&logoColor=white)](https://go.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [API Reference](#api-reference)
4. [Getting Started](#getting-started)
   - [Python / FastAPI](#python--fastapi)
   - [Go (Standard Library)](#go-standard-library)
5. [Running Tests](#running-tests)
   - [Python Tests](#python-tests)
   - [Go Tests](#go-tests)
6. [Validation Rules](#validation-rules)
7. [How to Contribute](#how-to-contribute)
8. [Code of Conduct](#code-of-conduct)
9. [License](#license)

---

## Project Overview

The **User Preferences API** exposes a small set of endpoints that let client applications:

- **Read and update** per-user settings (theme, language, timezone, notification preferences).
- **Create orders** with product, quantity, and price validation.
- **Check service health** via a lightweight liveness probe.

The same business logic is implemented twice — once in Python using [FastAPI](https://fastapi.tiangolo.com/) and [Pydantic](https://docs.pydantic.dev/), and once in Go using nothing but the standard library — making it an ideal project for comparing idiomatic patterns across languages.

---

## Repository Structure

```
.
├── src/                         # Python / FastAPI implementation
│   ├── main.py                  # App entry-point; mounts all routers
│   ├── schemas.py               # Pydantic request / response schemas
│   ├── api/
│   │   ├── endpoints.py         # GET + PUT /api/v1/preferences/{user_id}
│   │   └── orders.py            # POST /api/v1/orders
│   └── db/                      # In-memory data stores
│
├── cmd/
│   └── server/
│       ├── main.go              # Go entry-point; wires router + repos + handlers
│       └── main_test.go         # Integration test for /health
│
├── internal/                    # Go internal packages
│   ├── models/
│   │   └── models.go            # Domain structs (UserSettings, Order)
│   ├── repository/
│   │   ├── preferences_repo.go  # In-memory PreferencesRepository
│   │   ├── preferences_repo_test.go
│   │   ├── orders_repo.go       # In-memory OrdersRepository
│   │   └── orders_repo_test.go
│   └── handlers/
│       ├── helpers.go           # Shared JSON helpers & error shapes
│       ├── preferences.go       # Preferences handlers
│       ├── preferences_test.go
│       ├── orders.go            # Orders handler
│       └── orders_test.go
│
├── tests/                       # Python test suite
├── go.mod                       # Go module definition
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
└── README.md                    # This file
```

---

## API Reference

Both implementations expose the same HTTP contract on **port 8080** by default.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe → `{"status": "ok"}` |
| `GET`  | `/api/v1/preferences/{user_id}` | Return preferences for a user |
| `PUT`  | `/api/v1/preferences/{user_id}` | Partial update of user preferences |
| `POST` | `/api/v1/orders` | Create a new order |

### Example: Read Preferences

```http
GET /api/v1/preferences/user-123
```

```json
{
  "user_id": "user-123",
  "theme": "dark",
  "language": "en",
  "notifications": true,
  "timezone": "UTC",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Example: Update Preferences

```http
PUT /api/v1/preferences/user-123
Content-Type: application/json

{
  "theme": "light",
  "timezone": "America/New_York"
}
```

### Example: Create an Order

```http
POST /api/v1/orders
Content-Type: application/json

{
  "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "quantity": 3,
  "price": "19.99"
}
```

---

## Getting Started

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Python | 3.11 |
| pip | 23+ |
| Go | 1.22 |

---

### Python / FastAPI

#### 1. Clone the repository

```bash
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github
```

#### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Start the development server

```bash
uvicorn src.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`.  
Interactive docs (Swagger UI) are served at `http://localhost:8080/docs`.  
ReDoc documentation is available at `http://localhost:8080/redoc`.

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Port the server listens on |
| `LOG_LEVEL` | `info` | Uvicorn log level (`debug`, `info`, `warning`, `error`) |

---

### Go (Standard Library)

#### 1. Clone the repository (if not already done)

```bash
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github
```

#### 2. Run directly

```bash
go run ./cmd/server
```

#### 3. Build and run the binary

```bash
go build -o api ./cmd/server
./api
```

The server starts on port **8080** by default. Override with:

```bash
PORT=9090 ./api
```

> **Note:** The Go implementation has **zero external dependencies** — it relies exclusively on the Go standard library (`net/http`, `encoding/json`, `crypto/rand`, `sync`).

---

## Running Tests

### Python Tests

The Python test suite uses [pytest](https://pytest.org/) with [httpx](https://www.python-httpx.org/) for async HTTP testing.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_preferences.py -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

### Go Tests

```bash
# Run all tests across every package
go test ./...

# Run tests with verbose output
go test ./... -v

# Run tests for a specific package
go test ./internal/handlers/... -v

# Run tests with race detector enabled
go test -race ./...
```

---

## Validation Rules

### Preferences (`PUT /api/v1/preferences/{user_id}`)

| Field | Rule |
|-------|------|
| `theme` | Must be `"light"` or `"dark"` |
| `language` | Must not be blank (if supplied) |
| `timezone` | Must not be blank (if supplied) |
| `notifications` | Must be a boolean (if supplied) |
| *(any)* | At least one field must be present in the request body |

### Orders (`POST /api/v1/orders`)

| Field | Rule |
|-------|------|
| `product_id` | Required; must be a valid UUID v4 string |
| `quantity` | Required; integer strictly greater than 0 |
| `price` | Required; decimal string or number ≥ `0.01` |

All validation errors return **HTTP 422 Unprocessable Entity** with a structured JSON body describing the offending field(s).

---

## How to Contribute

Contributions are welcome! Please follow the steps below to keep the workflow clean and reviewable.

### 1. Fork & clone

```bash
# Fork via the GitHub UI, then:
git clone https://github.com/<your-username>/skills-introduction-to-github.git
cd skills-introduction-to-github
```

### 2. Create a feature branch

Use a descriptive, kebab-case branch name prefixed with the issue key:

```bash
git checkout -b feature/AID-42-add-rate-limiting
```

### 3. Make your changes

- Follow the existing code style (PEP 8 for Python; `gofmt` for Go).
- Add or update tests to cover your changes.
- Keep commits small and focused; write meaningful commit messages:

  ```
  AID-42: Add token-bucket rate limiting to POST /api/v1/orders

  - Introduce RateLimiter middleware using Redis sliding window
  - Return HTTP 429 with Retry-After header on limit breach
  - Add unit tests covering per-user and global limits
  ```

### 4. Run the test suite locally

```bash
# Python
pytest -v

# Go
go test ./...
```

All tests must pass before you open a pull request.

### 5. Open a Pull Request

- Push your branch and open a PR against `main`.
- Fill in the PR template (summary, how to test, linked issue).
- Request a review from a maintainer.
- Address any feedback and keep the branch up-to-date with `main`.

### 6. After merge

Delete your feature branch once the PR is merged:

```bash
git branch -d feature/AID-42-add-rate-limiting
git push origin --delete feature/AID-42-add-rate-limiting
```

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md). By participating, you agree to uphold a welcoming, respectful, and harassment-free environment for everyone.

Please report unacceptable behaviour to the repository maintainers.

---

## License

Copyright © 2025 GitHub, Inc.

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for the full text.

> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the above copyright notice and this permission notice being included in all copies or substantial portions of the Software.

---

*Built with ❤️ as part of the [GitHub Skills: Introduction to GitHub](https://skills.github.com/) learning path.*
