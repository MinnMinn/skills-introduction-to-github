# User Preferences & Orders API

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-e92063?logo=pydantic&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen?logo=pytest&logoColor=white)

A lightweight, production-ready REST API built with **FastAPI** and **Pydantic v2** that exposes two resource domains:

- **User Preferences** — store and retrieve per-user application settings (theme, language, notifications, timezone).
- **Orders** — create and validate new orders with strict business-rule enforcement at the schema level.

The service is intentionally small and self-contained, making it an ideal starting point for learning GitHub workflows, REST API design patterns, and Python testing practices.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Repository Structure](#repository-structure)
4. [API Reference](#api-reference)
   - [Health Check](#health-check)
   - [Preferences Endpoints](#preferences-endpoints)
   - [Orders Endpoints](#orders-endpoints)
5. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
6. [Running the Server](#running-the-server)
7. [Running Tests](#running-tests)
8. [Contributing](#contributing)
9. [License](#license)

---

## Features

- ✅ **Partial updates** — `PUT /api/v1/preferences/{user_id}` accepts any subset of preference fields; only supplied fields are changed.
- ✅ **Strict validation** — Orders enforce UUID format, positive quantity, and minimum unit price via Pydantic field validators.
- ✅ **Dependency injection** — Repository instances are injected via FastAPI `Depends`, making every endpoint trivially testable.
- ✅ **Interactive docs** — Auto-generated Swagger UI at `/docs` and ReDoc at `/redoc`.
- ✅ **Liveness probe** — `GET /health` returns `{"status": "ok"}` for orchestration health checks.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) 0.111 |
| Data validation | [Pydantic](https://docs.pydantic.dev/) v2.7 |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) 0.29 (with `standard` extras) |
| Testing | [Pytest](https://pytest.org/) 8.2 + [HTTPX](https://www.python-httpx.org/) 0.27 |
| Language | Python 3.11+ |

---

## Repository Structure

```
skills-introduction-to-github/
├── src/
│   ├── __init__.py
│   ├── main.py            # FastAPI application factory, router registration
│   ├── schemas.py         # Pydantic request/response models
│   └── api/
│       ├── __init__.py
│       ├── endpoints.py   # GET & PUT /api/v1/preferences/{user_id}
│       └── orders.py      # POST /api/v1/orders
│   └── db/
│       └── repos/
│           ├── preferences_repo.py  # PreferencesRepository
│           └── orders_repo.py       # OrdersRepository
├── tests/
│   ├── __init__.py
│   ├── test_orders.py        # Full test suite for the Orders API
│   └── test_preferences.py   # Full test suite for the Preferences API
├── requirements.txt       # Pinned Python dependencies
├── .gitignore
├── LICENSE                # MIT
└── README.md              # This file
```

---

## API Reference

All routes are prefixed with `/api/v1` except the health endpoint. The API returns JSON for every response. Validation errors automatically return **HTTP 422 Unprocessable Entity** with field-level details.

### Health Check

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — always returns `200 OK` |

**Response**
```json
{ "status": "ok" }
```

---

### Preferences Endpoints

#### `GET /api/v1/preferences/{user_id}`

Retrieve the current preferences for the given user.

**Path parameter**

| Name | Type | Description |
|------|------|-------------|
| `user_id` | `string` | Unique identifier of the user |

**Example request**
```bash
curl http://localhost:8000/api/v1/preferences/user-42
```

**200 OK — example response**
```json
{
  "user_id": "user-42",
  "theme": "dark",
  "language": "en",
  "notifications": true,
  "timezone": "UTC",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | No user with the given `user_id` exists |

---

#### `PUT /api/v1/preferences/{user_id}`

Partially update preferences for the given user. All body fields are **optional** — only fields present in the payload are modified (PATCH-style semantics over PUT).

**Path parameter**

| Name | Type | Description |
|------|------|-------------|
| `user_id` | `string` | Unique identifier of the user |

**Request body** (all fields optional, but at least one required)

| Field | Type | Allowed values |
|-------|------|----------------|
| `theme` | `string` | `"light"` or `"dark"` |
| `language` | `string` | Any non-blank BCP-47 language tag |
| `notifications` | `boolean` | `true` or `false` |
| `timezone` | `string` | Any non-blank timezone string (e.g. `"America/New_York"`) |

**Example request**
```bash
curl -X PUT http://localhost:8000/api/v1/preferences/user-42 \
     -H "Content-Type: application/json" \
     -d '{"theme": "light", "notifications": false}'
```

**200 OK — example response**
```json
{
  "user_id": "user-42",
  "theme": "light",
  "language": "en",
  "notifications": false,
  "timezone": "UTC",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | No user with the given `user_id` exists |
| `422 Unprocessable Entity` | No fields supplied, blank language/timezone, or invalid theme value |

---

### Orders Endpoints

#### `POST /api/v1/orders`

Create a new order. All three body fields are **required** and strictly validated.

**Request body**

| Field | Type | Rules |
|-------|------|-------|
| `product_id` | `string` | Must be a valid UUID v4 |
| `quantity` | `integer` | Must be > 0 |
| `price` | `number` | Must be ≥ 0.01 (decimal precision supported) |

**Example request**
```bash
curl -X POST http://localhost:8000/api/v1/orders \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "550e8400-e29b-41d4-a716-446655440000",
       "quantity": 3,
       "price": "19.99"
     }'
```

**201 Created — example response**
```json
{
  "order_id": "a1b2c3d4-...",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 3,
  "price": "19.99",
  "status": "pending",
  "created_at": "2025-01-15T11:05:00Z"
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `422 Unprocessable Entity` | Invalid UUID, `quantity` ≤ 0, `price` < 0.01, or missing required field |

---

## Getting Started

### Prerequisites

- **Python 3.11 or higher** — [Download](https://www.python.org/downloads/)
- **pip** — bundled with Python
- **Git** — [Download](https://git-scm.com/downloads)
- *(Optional)* **virtualenv** or the built-in `venv` module (recommended)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/MinnMinn/skills-introduction-to-github.git
   cd skills-introduction-to-github
   ```

2. **Create and activate a virtual environment** *(recommended)*

   ```bash
   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Server

Start the development server with hot-reload enabled:

```bash
uvicorn src.main:app --reload
```

The API will be available at:

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/health` | Liveness probe |

To bind to a different host or port:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 9000
```

---

## Running Tests

The test suite uses **Pytest** and **HTTPX** (via FastAPI's `TestClient`) — no running server is needed.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_orders.py -v
pytest tests/test_preferences.py -v

# Run with coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

All tests are located in the `tests/` directory and follow the naming convention `test_<resource>.py`.

---

## Contributing

Contributions are welcome! Please follow the steps below to keep the workflow consistent.

1. **Fork** the repository and clone your fork locally.

2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-descriptive-name
   ```

3. **Make your changes**, following the existing code style:
   - Route handlers live in `src/api/`.
   - Pydantic schemas live in `src/schemas.py`.
   - All repository (DB) access is encapsulated in `src/db/repos/`.
   - Every new endpoint or schema change should be accompanied by tests in `tests/`.

4. **Run the tests** to make sure nothing is broken:
   ```bash
   pytest -v
   ```

5. **Commit** with a clear, imperative message:
   ```bash
   git commit -m "feat: add DELETE /api/v1/orders/{order_id} endpoint"
   ```

6. **Push** your branch and **open a Pull Request** against `main`.
   - Fill in the PR description explaining *what* changed and *why*.
   - Link any related GitHub Issues or Jira tickets.

7. A maintainer will review your PR. Address any requested changes and the PR will be merged once approved.

### Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions.
- Use type hints on all function signatures.
- Keep docstrings concise and meaningful.
- Do not commit secrets, credentials, or environment-specific configuration.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for the full text.

```
Copyright (c) GitHub, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

> Built with ❤️ using [FastAPI](https://fastapi.tiangolo.com/) · [Back to top](#user-preferences--orders-api)
