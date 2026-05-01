"""FastAPI application entry point."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.profile.email import router as email_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Skills API", version="0.1.0")

# ── Convert Pydantic validation errors on request bodies to HTTP 400 ──────
# (Pydantic raises 422 by default; the spec calls for 400 on bad email.)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail},
    )


app.include_router(email_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
