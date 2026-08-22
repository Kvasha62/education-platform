"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    database_url: str
    minio_endpoint: str
    frontend_origin: str
    auth_cookie_secure: bool
    auth_session_ttl_seconds: int


def get_settings() -> Settings:
    """Load configuration from environment variables with safe local defaults."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://education:local_development_only@localhost:5432/education_platform",
        ),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/"),
        auth_cookie_secure=_bool_env("AUTH_COOKIE_SECURE", False),
        auth_session_ttl_seconds=int(os.getenv("AUTH_SESSION_TTL_SECONDS", "86400")),
    )
