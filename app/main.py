"""FastAPI application entrypoint."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers import profile

app = FastAPI(
    title="Profile API",
    description="User profile management endpoints.",
    version="0.1.0",
)

app.include_router(profile.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 400 (not 422) for request validation errors with a clear message."""
    errors = exc.errors()
    # Build a human-readable message from the first error
    first = errors[0] if errors else {}
    loc = " → ".join(str(l) for l in first.get("loc", []))
    msg = first.get("msg", "Invalid request.")
    detail = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        status_code=400,
        content={"detail": detail},
    )
