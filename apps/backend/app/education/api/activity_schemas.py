"""Pydantic contracts for Activity endpoints."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.education.domain.models import Activity, ActivityType


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


class CreateActivityRequest(_TitleMixin):
    title: str
    type: ActivityType
    position: int = Field(ge=0)


class UpdateActivityRequest(_TitleMixin):
    title: str | None = None
    position: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.title is None and self.position is None:
            raise ValueError("at least one field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title must not be null")
        if "position" in self.model_fields_set and self.position is None:
            raise ValueError("position must not be null")
        return self


class ActivityResponse(BaseModel):
    id: UUID
    learning_unit_id: UUID
    title: str
    type: ActivityType
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_activity(cls, activity: Activity) -> "ActivityResponse":
        return cls(
            id=activity.id,
            learning_unit_id=activity.learning_unit_id,
            title=activity.title,
            type=activity.type,
            position=activity.position,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
        )
