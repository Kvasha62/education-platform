"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.casefold() in {"1", "true", "yes", "on"}


def _positive_int_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    database_url: str
    minio_endpoint: str
    frontend_origin: str
    auth_cookie_secure: bool
    auth_session_ttl_seconds: int
    auth_login_rate_limit: int
    auth_register_rate_limit: int
    auth_rate_limit_window_seconds: int


def get_settings() -> Settings:
    """Load configuration from environment variables with safe local defaults."""
    app_env = os.getenv("APP_ENV", "development")
    return Settings(
        app_env=app_env,
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://education:local_development_only@localhost:5432/education_platform",
        ),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/"),
        auth_cookie_secure=_bool_env("AUTH_COOKIE_SECURE", app_env != "development"),
        auth_session_ttl_seconds=int(os.getenv("AUTH_SESSION_TTL_SECONDS", "86400")),
        auth_login_rate_limit=_positive_int_env("AUTH_LOGIN_RATE_LIMIT", 10),
        auth_register_rate_limit=_positive_int_env("AUTH_REGISTER_RATE_LIMIT", 5),
        auth_rate_limit_window_seconds=_positive_int_env("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60),
    )
