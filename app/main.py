"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers import profile

app = FastAPI(
    title="Skills API",
    description="API for the skills-introduction-to-github project.",
    version="0.1.0",
)

app.include_router(profile.router)


@app.get("/health", tags=["ops"])
def health_check() -> dict:
    return {"status": "ok"}
