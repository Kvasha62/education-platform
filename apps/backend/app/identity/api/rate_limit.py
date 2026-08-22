"""Rate-limit dependencies for public authentication endpoints."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter

login_limiter = InMemoryRateLimiter()
register_limiter = InMemoryRateLimiter()


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce(
    limiter: InMemoryRateLimiter,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    retry_after = limiter.check(key, limit, window_seconds)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_login_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    _enforce(
        login_limiter,
        _client_key(request),
        settings.auth_login_rate_limit,
        settings.auth_rate_limit_window_seconds,
    )


def enforce_register_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    _enforce(
        register_limiter,
        _client_key(request),
        settings.auth_register_rate_limit,
        settings.auth_rate_limit_window_seconds,
    )
