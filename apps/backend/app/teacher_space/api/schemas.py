"""Pydantic contracts for the Teacher Space API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.teacher_space.domain.models import TeacherSpace, TeacherSpaceStatus


class _NameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class CreateTeacherSpaceRequest(_NameRequest):
    pass


class UpdateTeacherSpaceRequest(_NameRequest):
    pass


class TeacherSpaceResponse(BaseModel):
    id: UUID
    name: str
    status: TeacherSpaceStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_teacher_space(cls, teacher_space: TeacherSpace) -> "TeacherSpaceResponse":
        return cls(
            id=teacher_space.id,
            name=teacher_space.name,
            status=teacher_space.status,
            created_at=teacher_space.created_at,
            updated_at=teacher_space.updated_at,
        )
