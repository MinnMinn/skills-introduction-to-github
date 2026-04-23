# ---------------------------------------------------------------------------
# Dockerfile — multi-stage build for the User Preferences API
# Equivalent of docker/Dockerfile in the standard Go layout.
# ---------------------------------------------------------------------------

# ── Stage 1: build / dependency installation ────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into a separate layer for better cache reuse
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY cmd/       cmd/
COPY internal/  internal/
COPY pkg/       pkg/
COPY config/    config/

# Drop to non-root
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "cmd.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
