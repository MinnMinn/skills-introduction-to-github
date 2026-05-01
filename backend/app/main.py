"""
FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import payments

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="Payments API",
    description="Stripe card-payment checkout — KAN-19",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(payments.router)


@app.get("/health", tags=["ops"])
async def health_check():
    return {"status": "ok", "service": "payments-api"}
