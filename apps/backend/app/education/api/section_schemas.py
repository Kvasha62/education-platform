"""Pydantic contracts for Section endpoints."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.education.domain.models import Section


class _SectionTitleMixin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("title", check_fields=False)
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        if len(normalized) > 120:
            raise ValueError("title must be at most 120 characters")
        return normalized


class CreateSectionRequest(_SectionTitleMixin):
    title: str
    position: int = Field(ge=0)


class UpdateSectionRequest(_SectionTitleMixin):
    title: str | None = None
    position: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.title is None and self.position is None:
            raise ValueError("at least one field must be provided")
        return self


class SectionResponse(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_section(cls, section: Section) -> "SectionResponse":
        return cls(
            id=section.id,
            course_id=section.course_id,
            title=section.title,
            position=section.position,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )
