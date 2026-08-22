"""Reusable FastAPI identity dependencies."""

from datetime import timedelta
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.identity.application.errors import InvalidSessionError
from app.identity.application.services import IdentityService
from app.identity.domain.models import Identity
from app.identity.infrastructure.passwords import Argon2PasswordService
from app.identity.infrastructure.repositories import (
    SqlAlchemyIdentityRepository,
    SqlAlchemySessionRepository,
)

SESSION_COOKIE_NAME = "education_session"
password_service = Argon2PasswordService()


def get_identity_service(
    db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> IdentityService:
    return IdentityService(
        SqlAlchemyIdentityRepository(db),
        password_service,
        SqlAlchemySessionRepository(db),
        timedelta(seconds=settings.auth_session_ttl_seconds),
    )


def get_session_token(
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> str:
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return session_token


def get_current_identity(
    token: Annotated[str, Depends(get_session_token)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> Identity:
    """Public dependency future modules use to identify the caller."""
    try:
        return service.authenticate(token)
    except InvalidSessionError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required") from error


def require_trusted_origin(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> None:
    """Protect cookie-authenticated state changes from cross-site requests."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    if origin == settings.frontend_origin:
        return
    if referer and referer.startswith(f"{settings.frontend_origin}/"):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Untrusted request origin")
