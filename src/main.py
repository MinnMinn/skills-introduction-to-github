"""FastAPI application entry point."""
from fastapi import FastAPI

from src.api.endpoints import router as preferences_router
from src.db.database import Base, engine

# Create all tables on startup (suitable for development / SQLite).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Preferences API",
    description="Manage per-user application preferences.",
    version="0.1.0",
)

app.include_router(preferences_router)


@app.get("/health")
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
