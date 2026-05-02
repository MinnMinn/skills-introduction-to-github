"""
FastAPI application factory.

Startup sequence
----------------
1. Validate that JWT_SECRET is present and long enough (fails fast).
2. Create DB tables if they do not exist.
3. Mount routers.
"""
from __future__ import annotations

import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import create_tables
from app.routers.login import router as login_router

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            # Audit logger — route to persistent sink in production.
            "audit.login": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
    }
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    # Validate JWT_SECRET at startup — raises RuntimeError if missing/short.
    get_settings().jwt_secret  # noqa: B018

    app = FastAPI(
        title="Login Service",
        description="Provides POST /api/login for user authentication.",
        version="0.1.0",
        # Disable default docs in production if desired via env-var.
    )

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover
        create_tables()

    # ------------------------------------------------------------------ #
    # Exception handlers
    # ------------------------------------------------------------------ #

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Return HTTP 400 with a descriptive validation error.
        Never expose stack traces; password values are not logged by Pydantic
        because the schema uses `exclude` semantics and the error only
        contains field names + messages.
        """
        # Build a sanitised error list — omit any 'input' values that might
        # contain the password field.
        errors = []
        for e in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in e["loc"]),
                    "message": e["msg"],
                    "type": e["type"],
                }
            )
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "detail": errors},
        )

    app.include_router(login_router)

    return app


app = create_app()
