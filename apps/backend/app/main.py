"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.identity.api import router as identity_router

settings = get_settings()
app = FastAPI(title="Education Platform API", version="0.1.0")
app.include_router(identity_router)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Report process health without depending on external services."""
    return {"status": "ok", "environment": settings.app_env}
