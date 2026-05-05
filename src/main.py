"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.api.endpoints import router as preferences_router
from src.db.database import engine
from src.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create all tables on startup (idempotent — does not modify existing schema)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="User Preferences API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(preferences_router)
