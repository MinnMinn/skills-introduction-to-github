# User Preferences API

![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/tests-pytest-brightgreen?logo=pytest&logoColor=white)

A lightweight REST API built with **FastAPI** for managing per-user application preferences and orders. It exposes a clean JSON interface, enforces strict input validation via **Pydantic v2**, and is fully covered by an automated test suite.

---

## Table of Contents

- [Description](#description)
- [Quick Start](#quick-start)
- [Setup](#setup)
- [Usage](#usage)
  - [Health Check](#health-check)
  - [Preferences API](#preferences-api)
  - [Orders API](#orders-api)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

---

## Description

**User Preferences API** provides two core feature areas:

| Feature | Description |
|---|---|
| **Preferences** | Store and retrieve per-user settings (theme, language, notifications, timezone) |
| **Orders** | Create validated orders linked to a product, quantity, and price |

Key characteristics:

- 🚀 **FastAPI** — high-performance async framework with automatic OpenAPI docs
- 🔒 **Pydantic v2** — strict schema validation on every request
- 🧪 **pytest + httpx** — full unit and integration test coverage
- 📄 **Auto-generated docs** — interactive Swagger UI available at `/docs`

---

## Quick Start

```bash
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

The API will be available at **http://127.0.0.1:8000**.  
Interactive docs are at **http://127.0.0.1:8000/docs**.

---

## Setup

### Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11 |
| pip | 23+ |

### Step-by-step

1. **Clone the repository**

   ```bash
   git clone https://github.com/MinnMinn/skills-introduction-to-github.git
   cd skills-introduction-to-github
   ```

2. **Create and activate a virtual environment**

   ```bash
   # macOS / Linux
   python -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   | Package | Version | Purpose |
   |---|---|---|
   | fastapi | 0.111.0 | Web framework |
   | uvicorn[standard] | 0.29.0 | ASGI server |
   | pydantic | 2.7.1 | Request/response validation |
   | pytest | 8.2.0 | Test runner |
   | httpx | 0.27.0 | Async HTTP client (used in tests) |

4. **Run the development server**

   ```bash
   uvicorn src.main:app --reload
   ```

   Use `--host 0.0.0.0 --port 8080` to bind to a custom address/port.

---

## Usage

All API routes are prefixed with `/api/v1`. Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the server is running.

### Health Check

Verify the service is alive:

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status": "ok"}
```

---

### Preferences API

#### `GET /api/v1/preferences/{user_id}` — Retrieve user preferences

```bash
curl http://127.0.0.1:8000/api/v1/preferences/user-42
```

**200 OK**

```json
{
  "user_id": "user-42",
  "theme": "dark",
  "language": "en",
  "notifications": true,
  "timezone": "America/New_York",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**404 Not Found** — when the user does not exist.

```json
{"detail": "User 'user-42' not found"}
```

---

#### `PUT /api/v1/preferences/{user_id}` — Update user preferences

Supports **partial updates** — only include the fields you want to change. At least one field is required.

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/preferences/user-42 \
     -H "Content-Type: application/json" \
     -d '{"theme": "light", "notifications": false}'
```

**Request body fields** (all optional, at least one required):

| Field | Type | Allowed values |
|---|---|---|
| `theme` | string | `"light"` \| `"dark"` |
| `language` | string | Any non-blank string (e.g. `"en"`, `"fr"`) |
| `notifications` | boolean | `true` \| `false` |
| `timezone` | string | Any non-blank string (e.g. `"UTC"`, `"Europe/London"`) |

**200 OK** — returns the full updated preferences object.

**404 Not Found** — user does not exist.

**422 Unprocessable Entity** — validation error (e.g. empty body, blank language).

---

### Orders API

#### `POST /api/v1/orders` — Create a new order

```bash
curl -X POST http://127.0.0.1:8000/api/v1/orders \
     -H "Content-Type: application/json" \
     -d '{
           "product_id": "550e8400-e29b-41d4-a716-446655440000",
           "quantity": 3,
           "price": "19.99"
         }'
```

**Request body fields** (all required):

| Field | Type | Constraints |
|---|---|---|
| `product_id` | string (UUID v4) | Must be a valid UUID |
| `quantity` | integer | Must be > 0 |
| `price` | decimal string | Must be ≥ 0.01 |

**201 Created**

```json
{
  "order_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "product_id": "550e8400-e29b-41d4-a716-446655440000",
  "quantity": 3,
  "price": "19.99",
  "status": "pending",
  "created_at": "2025-01-15T10:35:00Z"
}
```

**422 Unprocessable Entity** — returned automatically by FastAPI when any field fails validation (invalid UUID, quantity ≤ 0, price < 0.01).

---

## Running Tests

The test suite uses **pytest** with **httpx** for in-process API testing — no running server required.

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

---

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository on GitHub.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**, following the existing code style:
   - Route handlers go in `src/api/`
   - Pydantic schemas go in `src/schemas.py`
   - Write or update tests in `tests/`
4. **Run the tests** to make sure everything passes:
   ```bash
   pytest -v
   ```
5. **Commit** your changes with a clear, descriptive message:
   ```bash
   git commit -m "feat: add short description of change"
   ```
6. **Push** your branch and **open a Pull Request** against `main`.
7. Fill in the PR description explaining *what* changed and *why*.

Please ensure your PR:
- Passes all existing tests
- Includes tests for any new functionality
- Does not introduce hardcoded secrets or credentials

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Copyright © GitHub, Inc.
