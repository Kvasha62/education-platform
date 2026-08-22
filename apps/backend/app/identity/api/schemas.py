"""Pydantic contracts for the public authentication API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.identity.domain.models import Identity, IdentityStatus


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class IdentityResponse(BaseModel):
    id: UUID
    email: EmailStr
    status: IdentityStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_identity(cls, identity: Identity) -> "IdentityResponse":
        return cls(
            id=identity.id,
            email=identity.email,
            status=identity.status,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )


class LoginResponse(BaseModel):
    user: IdentityResponse


class LogoutResponse(BaseModel):
    status: str = "logged_out"
