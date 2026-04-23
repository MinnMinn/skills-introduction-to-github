"""
Application entry-point.

Equivalent of cmd/api/main.go in the standard Go layout.

Mounts all API routers, registers middleware, and configures the FastAPI
application.  All wiring happens here so that individual packages remain
importable without side-effects.

Run locally:
    uvicorn cmd.api.main:app --reload

Or via the Makefile:
    make run
"""

from __future__ import annotations

from fastapi import FastAPI

from config.config import get_settings
from internal.handler.user_handler import router as preferences_router
from internal.middleware.auth import AuthMiddleware
from pkg.logger import get_logger

settings = get_settings()
log = get_logger(__name__)

app = FastAPI(
    title="User Preferences API",
    description="Manage per-user application preferences.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(AuthMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(preferences_router)


# ---------------------------------------------------------------------------
# Utility routes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["ops"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dev server entry-point  (python cmd/api/main.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    log.info("Starting server on %s:%d", settings.app_host, settings.app_port)
    uvicorn.run(
        "cmd.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )
