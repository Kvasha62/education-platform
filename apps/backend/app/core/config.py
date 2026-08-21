"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    database_url: str
    minio_endpoint: str


def get_settings() -> Settings:
    """Load configuration from environment variables with safe local defaults."""
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://education:local_development_only@localhost:5432/education_platform",
        ),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
    )
