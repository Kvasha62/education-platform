"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="Education Platform API", version="0.1.0")


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Report process health without depending on external services."""
    return {"status": "ok", "environment": settings.app_env}
