# Skills — Introduction to GitHub

> A lightweight **FastAPI** service that demonstrates REST API design, Pydantic validation,
> and a clean repository pattern — used as a hands-on GitHub learning exercise.

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-orange.svg)](https://docs.pytest.org/)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [API Reference](#api-reference)
   - [Health Check](#health-check)
   - [Preferences API](#preferences-api)
   - [Orders API](#orders-api)
4. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Running the Server](#running-the-server)
5. [Running Tests](#running-tests)
6. [Project Structure](#project-structure)
7. [How to Contribute](#how-to-contribute)
8. [License](#license)

---

## Project Overview

This repository is a fully-functional **REST API** built with [FastAPI](https://fastapi.tiangolo.com/).
It exposes two resource domains:

| Domain          | Description                                        |
|-----------------|----------------------------------------------------|
| **Preferences** | Store and retrieve per-user application settings   |
| **Orders**      | Create validated customer orders                   |

The project serves as the practical backend for the *Introduction to GitHub* skills exercise,
illustrating real-world patterns such as:

- **Repository pattern** — all database access is isolated behind repository classes
- **Pydantic v2 validation** — request schemas enforce types, ranges, and non-blank strings
- **Dependency injection** — repositories are injected via FastAPI `Depends`, making tests easy
- **Auto-generated docs** — interactive Swagger UI available at `/docs` out of the box

---

## Architecture

```
skills-introduction-to-github/
├── src/
│   ├── main.py          # FastAPI app factory; mounts all routers
│   ├── schemas.py       # Pydantic request / response schemas
│   ├── api/
│   │   ├── endpoints.py # GET & PUT /api/v1/preferences/{user_id}
│   │   └── orders.py    # POST /api/v1/orders
│   └── db/
│       ├── models.py    # Dataclass models (UserSettings, Order)
│       └── repos/       # Repository implementations
├── tests/
│   ├── test_orders.py       # Test suite for the Orders API
│   └── test_preferences.py  # Test suite for the Preferences API
├── requirements.txt
└── LICENSE
```

The application is intentionally small and self-contained — there is **no external database
dependency**; the repositories hold state in-memory so the project runs with zero
infrastructure setup.

---

## API Reference

All routes are prefixed with `/api/v1`. Interactive documentation is served by FastAPI at
`http://localhost:8000/docs` when the server is running.

### Health Check

| Method | Path      | Description           |
|--------|-----------|-----------------------|
| `GET`  | `/health` | Liveness probe        |

**Response `200 OK`**
```json
{ "status": "ok" }
```

---

### Preferences API

Manage per-user application settings (theme, language, notifications, timezone).

| Method | Path                                   | Description                      |
|--------|----------------------------------------|----------------------------------|
| `GET`  | `/api/v1/preferences/{user_id}`        | Retrieve preferences for a user  |
| `PUT`  | `/api/v1/preferences/{user_id}`        | Partially update preferences     |

#### GET `/api/v1/preferences/{user_id}`

Returns the full preferences object for the given `user_id`.

**Response `200 OK`**
```json
{
  "user_id": "alice",
  "theme": "dark",
  "language": "en",
  "notifications": true,
  "timezone": "America/New_York",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Response `404 Not Found`** — user does not exist.

---

#### PUT `/api/v1/preferences/{user_id}`

Performs a **partial update** (PATCH-style semantics over PUT). Only the fields present in the
request body are changed; omitted fields keep their current values.

**Request body** *(all fields optional, but at least one is required)*
```json
{
  "theme": "light",
  "language": "fr",
  "notifications": false,
  "timezone": "Europe/Paris"
}
```

| Field           | Type                      | Rules                              |
|-----------------|---------------------------|------------------------------------|
| `theme`         | `"light"` \| `"dark"`    | Enumerated values only             |
| `language`      | `string`                  | Must not be blank                  |
| `notifications` | `boolean`                 | —                                  |
| `timezone`      | `string`                  | Must not be blank                  |

**Response `200 OK`** — returns the updated preferences object (same shape as GET).  
**Response `404 Not Found`** — user does not exist.  
**Response `422 Unprocessable Entity`** — validation error or no fields supplied.

---

### Orders API

Create new customer orders with strict validation.

| Method | Path               | Description        |
|--------|--------------------|--------------------|
| `POST` | `/api/v1/orders`   | Create a new order |

#### POST `/api/v1/orders`

**Request body**
```json
{
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 3,
  "price": "19.99"
}
```

| Field        | Type      | Rules                      |
|--------------|-----------|----------------------------|
| `product_id` | `string`  | Must be a valid UUID v4    |
| `quantity`   | `integer` | Must be `> 0`              |
| `price`      | `decimal` | Must be `>= 0.01`          |

**Response `201 Created`**
```json
{
  "order_id": "a1b2c3d4-...",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 3,
  "price": "19.99",
  "status": "pending",
  "created_at": "2025-01-15T10:31:00+00:00"
}
```

**Response `422 Unprocessable Entity`** — validation error (bad UUID, quantity ≤ 0, price < 0.01).

---

## Getting Started

### Prerequisites

- **Python 3.11** or newer ([download](https://www.python.org/downloads/))
- **pip** (bundled with Python)
- *(Optional)* [virtualenv](https://virtualenv.pypa.io/) or the built-in `venv` module

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
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

```bash
uvicorn src.main:app --reload
```

The API will be available at:

| URL                                | Purpose                    |
|------------------------------------|----------------------------|
| `http://localhost:8000/health`     | Liveness probe             |
| `http://localhost:8000/docs`       | Swagger UI (interactive)   |
| `http://localhost:8000/redoc`      | ReDoc documentation        |

---

## Running Tests

The test suite uses [pytest](https://docs.pytest.org/) and
[httpx](https://www.python-httpx.org/) via FastAPI's `TestClient`.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_orders.py -v
pytest tests/test_preferences.py -v

# Run with coverage report (requires pytest-cov)
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

All tests are fully self-contained — no external services or environment variables are needed.

---

## Project Structure

```
src/
├── __init__.py
├── main.py          # App entry-point; configures FastAPI and mounts routers
├── schemas.py       # All Pydantic schemas for requests and responses
├── api/
│   ├── __init__.py
│   ├── endpoints.py # Preferences router (GET, PUT)
│   └── orders.py    # Orders router (POST)
└── db/
    ├── __init__.py
    ├── models.py    # UserSettings and Order dataclasses
    └── repos/       # PreferencesRepository and OrdersRepository

tests/
├── __init__.py
├── test_preferences.py
└── test_orders.py
```

**Key design decisions:**

- **Schemas live in one file** (`schemas.py`) — keeps import paths simple and avoids circular
  imports between routers.
- **Repositories are injected** — each router exposes a `get_repo()` dependency, which tests
  override via `app.dependency_overrides` to pass in stub repositories.
- **No float arithmetic for money** — order prices are stored and transported as `str` to
  avoid IEEE-754 rounding surprises.

---

## How to Contribute

Contributions are welcome! Please follow these steps:

1. **Fork** the repository on GitHub.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**, following the existing code style (type hints, docstrings, etc.).
4. **Write or update tests** for your changes — all new code should be covered.
5. **Run the test suite** and ensure everything passes:
   ```bash
   pytest -v
   ```
6. **Commit** with a clear, imperative message:
   ```bash
   git commit -m "Add support for order cancellation endpoint"
   ```
7. **Push** your branch and open a **Pull Request** against `main`.

### Code Style Guidelines

- Follow [PEP 8](https://peps.python.org/pep-0008/) for formatting.
- Use type annotations on all function signatures.
- Write docstrings for all public functions, classes, and modules.
- Keep each router focused on one resource; add new resources in a new file under `src/api/`.
- Do **not** modify `src/db/models.py` column definitions — they reflect live DB tables.

### Reporting Issues

Please [open a GitHub Issue](https://github.com/MinnMinn/skills-introduction-to-github/issues)
with a clear description of the bug or feature request. Include steps to reproduce for bugs.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for the
full text.

```
Copyright (c) GitHub, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

<sub>&copy; 2025 GitHub &bull; [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md) &bull; [MIT License](LICENSE)</sub>
