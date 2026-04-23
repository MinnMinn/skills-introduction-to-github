"""
Application entry-point.

Mounts all API routers and configures the FastAPI application.
"""

from fastapi import FastAPI

from src.api.endpoints import router as preferences_router
from src.api.orders import router as orders_router

app = FastAPI(
    title="User Preferences API",
    description="Manage per-user application preferences.",
    version="1.0.0",
)

app.include_router(preferences_router)
app.include_router(orders_router)


@app.get("/health", tags=["ops"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
