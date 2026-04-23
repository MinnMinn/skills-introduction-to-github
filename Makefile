# ---------------------------------------------------------------------------
# Makefile — build, run, test, and lint helpers
# Equivalent of the Makefile in the standard Go layout.
# ---------------------------------------------------------------------------

.PHONY: help run test lint fmt install clean

# Default target
help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install   Install Python dependencies"
	@echo "  run       Start the development server (hot-reload)"
	@echo "  test      Run the full test suite"
	@echo "  lint      Run ruff linter"
	@echo "  fmt       Auto-format source with ruff"
	@echo "  clean     Remove __pycache__ and .pytest_cache directories"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Start the development server
run:
	uvicorn cmd.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v

# Lint (requires ruff: pip install ruff)
lint:
	ruff check .

# Auto-format (requires ruff)
fmt:
	ruff format .

# Clean build artefacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info"   -exec rm -rf {} + 2>/dev/null || true
