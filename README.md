# User Preferences API

A lightweight REST API built with [FastAPI](https://fastapi.tiangolo.com/) for managing per-user application preferences and orders.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)

---

## Table of Contents

- [Project Description](#project-description)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Running the Server](#running-the-server)
- [Running Tests](#running-tests)
- [How to Contribute](#how-to-contribute)
- [License](#license)

---

## Project Description

**User Preferences API** provides endpoints to create, read, update, and delete per-user preferences and orders. It is built on top of FastAPI and Pydantic for fast, type-safe request validation, and uses `pytest` + `httpx` for integration testing.

Key capabilities:
- Manage user preference settings (read/write)
- Manage user orders
- Health-check endpoint at `GET /health`
- Auto-generated interactive docs at `/docs` (Swagger UI) and `/redoc`

---

## Prerequisites

Before setting up the project, make sure you have the following installed:

| Tool | Purpose | Install guide |
|------|---------|---------------|
| **Git** | Clone the repository and manage branches | https://git-scm.com/downloads |
| **Python 3.10+** | Run the application and tests | https://www.python.org/downloads/ |
| **A text editor** | Edit source files (e.g. VS Code, Neovim, PyCharm) | — |
| **A GitHub account** | Fork, open issues, and submit pull requests | https://github.com/join |

> **Note:** These instructions cover **macOS** and **Linux**. Windows is not covered at this time.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github
```

### 2. Create and activate a virtual environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should now be prefixed with `(.venv)`.

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Server

Start the development server with auto-reload enabled:

```bash
uvicorn src.main:app --reload
```

The API will be available at:

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000` | API root |
| `http://127.0.0.1:8000/docs` | Swagger UI (interactive docs) |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation |
| `http://127.0.0.1:8000/health` | Health check endpoint |

To stop the server, press `Ctrl + C`.

---

## Running Tests

The test suite uses `pytest` and `httpx`. With the virtual environment active, run:

```bash
pytest
```

For verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_orders.py -v
pytest tests/test_preferences.py -v
```

---

## How to Contribute

Contributions are welcome! Please follow these steps:

1. **Fork** this repository by clicking the _Fork_ button at the top of the page.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/skills-introduction-to-github.git
   cd skills-introduction-to-github
   ```
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up** the project following the [Getting Started](#getting-started) instructions above.
5. **Make your changes**, write or update tests, and verify everything passes:
   ```bash
   pytest -v
   ```
6. **Commit** with a clear, descriptive message:
   ```bash
   git add .
   git commit -m "feat: describe what your change does"
   ```
7. **Push** your branch to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** against the `main` branch of this repository and describe what you changed and why.

Please keep pull requests focused — one feature or fix per PR. For significant changes, open an issue first to discuss your approach.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

Copyright © GitHub, Inc.
