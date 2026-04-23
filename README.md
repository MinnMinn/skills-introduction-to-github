# 🐙 Introduction to GitHub — Skills Project

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![pytest](https://img.shields.io/badge/tested%20with-pytest-yellow?logo=pytest)](https://docs.pytest.org/)

A hands-on GitHub Skills project that teaches the core GitHub workflow — issues, branches, commits, and pull requests — using a real **FastAPI** web service as the working codebase.

---

## 📖 Table of Contents

- [What This Project Is](#what-this-project-is)
- [⚡ Quick Start (experienced developers)](#-quick-start-experienced-developers)
- [🌱 Beginner Setup (new to Git & GitHub)](#-beginner-setup-new-to-git--github)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [How to Contribute](#how-to-contribute)
- [Running Tests](#running-tests)
- [License](#license)

---

## What This Project Is

This repository is a [GitHub Skills](https://skills.github.com/) learning exercise that walks you through the fundamental GitHub workflow:

| Concept | What you'll practise |
|---|---|
| **Issues** | Tracking work and discussion |
| **Branches** | Isolating changes from the main codebase |
| **Commits** | Saving snapshots of your work |
| **Pull Requests** | Proposing and reviewing changes |

The "real" codebase underneath is a small **User Preferences & Orders API** built with:

- [FastAPI](https://fastapi.tiangolo.com/) — Python web framework
- [Pydantic v2](https://docs.pydantic.dev/) — data validation
- [pytest](https://docs.pytest.org/) + [httpx](https://www.python-httpx.org/) — testing

You don't need to know Python or FastAPI to complete the GitHub Skills exercise — but the code is there if you want to explore it.

---

## ⚡ Quick Start (experienced developers)

> Assumes Git, Python 3.11+, and a GitHub account are already set up.

```bash
# 1. Clone the repo
git clone https://github.com/MinnMinn/skills-introduction-to-github.git
cd skills-introduction-to-github

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the development server (reload on save)
uvicorn src.main:app --reload

# 5. Run the test suite
pytest
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`.

---

## 🌱 Beginner Setup (new to Git & GitHub)

Welcome! This section assumes you have never used Git or GitHub before. Take it one step at a time — you've got this. ☕

### What is Git?

**Git** is a *version control system*: a tool that tracks every change you make to your files. Think of it like "Track Changes" in a Word document, but for entire projects. It lets you:

- Save snapshots of your work (called **commits**)
- Experiment in separate **branches** without breaking working code
- Collaborate with others by sharing changes through a central server

### What is GitHub?

**GitHub** is a website that hosts Git repositories online and adds collaboration features on top: Issues, Pull Requests, Actions, and more. This project lives on GitHub.

---

### Step 1 — Install Git

| Operating System | Instructions |
|---|---|
| **macOS** | Install [Homebrew](https://brew.sh/) then run `brew install git`, **or** install [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/): `xcode-select --install` |
| **Windows** | Download and run the installer from [git-scm.com/download/win](https://git-scm.com/download/win). Accept all defaults. |
| **Linux (Debian/Ubuntu)** | `sudo apt update && sudo apt install git` |

Verify the installation:

```bash
git --version
# Expected output: git version 2.x.x
```

### Step 2 — Create a GitHub Account

If you don't already have one, sign up for free at [github.com](https://github.com/).

### Step 3 — Configure Git with your identity

Git stamps your name and email on every commit you make. Run these two commands once (replace the placeholders):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Step 4 — Install Python 3.11+

Download the installer for your OS from [python.org/downloads](https://www.python.org/downloads/).  
Verify with:

```bash
python --version
# Expected: Python 3.11.x  (or higher)
```

> **Windows tip:** During installation, tick **"Add Python to PATH"** before clicking Install.

### Step 5 — Fork this repository (your own copy)

A **fork** is your personal copy of someone else's repository on GitHub.

1. Make sure you're logged in to GitHub.
2. Click the **Fork** button at the top-right of this page.
3. GitHub creates `<your-username>/skills-introduction-to-github` — that's your playground.

### Step 6 — Clone your fork to your computer

**Cloning** downloads the repository to your local machine so you can work on it.

```bash
# Replace YOUR-USERNAME with your actual GitHub username
git clone https://github.com/YOUR-USERNAME/skills-introduction-to-github.git

# Move into the project folder
cd skills-introduction-to-github
```

### Step 7 — Create a virtual environment

A **virtual environment** is an isolated Python installation for this project so its packages don't conflict with other Python projects on your machine.

```bash
# Create the virtual environment (only need to do this once)
python -m venv .venv

# Activate it — you must do this every time you open a new terminal
# macOS / Linux:
source .venv/bin/activate

# Windows (Command Prompt):
.venv\Scripts\activate.bat

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

When active, your terminal prompt will start with `(.venv)`.

### Step 8 — Install project dependencies

```bash
pip install -r requirements.txt
```

### Step 9 — Run the application

```bash
uvicorn src.main:app --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Open `http://127.0.0.1:8000/docs` in your browser to see the interactive API documentation. Press `CTRL+C` to stop the server.

### Step 10 — Run the tests

```bash
pytest
```

All tests should pass. 🎉

---

## Project Structure

```
skills-introduction-to-github/
│
├── src/                        # Application source code
│   ├── main.py                 # FastAPI app entry-point; mounts routers
│   ├── schemas.py              # Pydantic request/response models
│   └── api/
│       ├── endpoints.py        # User Preferences routes (GET / POST / DELETE)
│       └── orders.py           # Orders routes (GET / POST / PATCH / DELETE)
│
├── tests/                      # Automated test suite (pytest)
│   ├── test_preferences.py     # Tests for preferences endpoints
│   └── test_orders.py          # Tests for orders endpoints
│
├── .github/
│   ├── workflows/              # GitHub Actions CI configuration
│   └── steps/                  # GitHub Skills step definitions
│
├── requirements.txt            # Python dependencies (pinned versions)
├── LICENSE                     # MIT License
└── README.md                   # You are here 📍
```

---

## API Overview

Once the server is running, the full interactive documentation is at `http://127.0.0.1:8000/docs`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `GET` | `/preferences/{user_id}` | Retrieve preferences for a user |
| `POST` | `/preferences/{user_id}` | Create or update preferences for a user |
| `DELETE` | `/preferences/{user_id}` | Delete preferences for a user |
| `GET` | `/orders` | List all orders |
| `POST` | `/orders` | Create a new order |
| `GET` | `/orders/{order_id}` | Retrieve a specific order |
| `PATCH` | `/orders/{order_id}` | Partially update an order |
| `DELETE` | `/orders/{order_id}` | Delete an order |

---

## How to Contribute

Contributions are welcome! Here's the workflow, whether you're a beginner or a seasoned developer:

### 1. Create a branch for your change

Never commit directly to `main`. A **branch** keeps your work isolated until it's ready.

```bash
# Create a branch and switch to it in one command
git checkout -b feature/your-short-description
```

### 2. Make your changes and commit them

```bash
# Stage the files you changed
git add .

# Save a snapshot with a descriptive message
git commit -m "feat: describe what you changed"
```

> **Good commit message tips:** start with a short verb (`feat:`, `fix:`, `docs:`, `test:`), keep it under 72 characters, and explain *what* and *why*, not *how*.

### 3. Push your branch to GitHub

```bash
git push origin feature/your-short-description
```

### 4. Open a Pull Request

1. Visit your fork on GitHub.
2. GitHub will show a banner: **"Compare & pull request"** — click it.
3. Fill in the title and description explaining your change.
4. Click **"Create pull request"**.

A maintainer will review your PR, leave feedback, and merge it when it's ready.

### Contribution Guidelines

- Follow the existing code style (PEP 8 for Python).
- Add or update tests for any behaviour you change — aim to keep `pytest` green.
- Keep pull requests small and focused on a single concern.
- Be kind and constructive in code review comments. ❤️

---

## Running Tests

```bash
# Run the full test suite
pytest

# Run with verbose output (shows individual test names)
pytest -v

# Run only a specific test file
pytest tests/test_orders.py

# Run tests and show coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for the full text.

Copyright © 2025 GitHub, Inc.

---

<p align="center">
  Made with ❤️ as part of <a href="https://skills.github.com/">GitHub Skills</a>
</p>
