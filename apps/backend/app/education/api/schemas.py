"""Pydantic contracts for Educational Environment endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.education.domain.models import EducationalEnvironment


class EnvironmentNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        if len(normalized) > 120:
            raise ValueError("name must be at most 120 characters")
        return normalized


class CreateEnvironmentRequest(EnvironmentNameRequest):
    pass


class UpdateEnvironmentRequest(EnvironmentNameRequest):
    pass


class EnvironmentResponse(BaseModel):
    id: UUID
    teacher_space_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_environment(cls, environment: EducationalEnvironment) -> "EnvironmentResponse":
        return cls(
            id=environment.id,
            teacher_space_id=environment.teacher_space_id,
            name=environment.name,
            created_at=environment.created_at,
            updated_at=environment.updated_at,
        )
