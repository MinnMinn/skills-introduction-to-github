"""
FastAPI application factory.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import auth

app = FastAPI(title="Reset-Password Service", version="0.1.0")

# ---------------------------------------------------------------------------
# Override FastAPI's default validation error handler so it returns a clean
# {"error": "<msg>"} body instead of the default verbose structure.
# This satisfies AC: malformed body → 400 with a validation error message.
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Collect human-readable messages from all validation errors.
    messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "validation error")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "; ".join(messages)},
    )


app.include_router(auth.router)
