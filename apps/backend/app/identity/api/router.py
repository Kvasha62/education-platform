"""Authentication HTTP endpoints; business logic remains in application services."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import Settings, get_settings
from app.identity.api.dependencies import (
    SESSION_COOKIE_NAME,
    get_current_identity,
    get_identity_service,
    get_session_token,
    require_trusted_origin,
)
from app.identity.api.schemas import (
    IdentityResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegistrationRequest,
)
from app.identity.application.errors import (
    DuplicateIdentityError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.identity.application.services import IdentityService
from app.identity.domain.models import Identity

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegistrationRequest,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> IdentityResponse:
    try:
        identity = service.register(str(payload.email), payload.password)
    except DuplicateIdentityError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Identity already exists") from error
    return IdentityResponse.from_identity(identity)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    try:
        identity, token = service.login(str(payload.email), payload.password)
    except InvalidCredentialsError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from error
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_seconds,
        path="/",
    )
    return LoginResponse(user=IdentityResponse.from_identity(identity))


@router.get("/me", response_model=IdentityResponse)
def me(identity: Annotated[Identity, Depends(get_current_identity)]) -> IdentityResponse:
    return IdentityResponse.from_identity(identity)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def logout(
    response: Response,
    token: Annotated[str, Depends(get_session_token)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> LogoutResponse:
    try:
        service.logout(token)
    except InvalidSessionError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required") from error
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return LogoutResponse()
