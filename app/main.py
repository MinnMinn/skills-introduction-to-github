"""
FastAPI application entry point.
"""
from fastapi import FastAPI

from app.routers import profile

app = FastAPI(
    title="Profile API",
    description="User profile management — email-change flow with JWT auth.",
    version="1.0.0",
)

app.include_router(profile.router)


@app.get("/health", tags=["ops"])
def health_check() -> dict:
    return {"status": "ok"}
