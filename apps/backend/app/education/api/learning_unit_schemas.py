"""Pydantic contracts for Learning Unit endpoints."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.education.domain.models import LearningUnit


class _TitleMixin(BaseModel):
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


class CreateLearningUnitRequest(_TitleMixin):
    title: str
    position: int = Field(ge=0)


class UpdateLearningUnitRequest(_TitleMixin):
    title: str | None = None
    position: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.title is None and self.position is None:
            raise ValueError("at least one field must be provided")
        return self


class LearningUnitResponse(BaseModel):
    id: UUID
    section_id: UUID
    title: str
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_unit(cls, unit: LearningUnit) -> "LearningUnitResponse":
        return cls(
            id=unit.id,
            section_id=unit.section_id,
            title=unit.title,
            position=unit.position,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
        )
