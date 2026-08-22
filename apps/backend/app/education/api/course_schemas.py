"""Pydantic contracts for Course endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.education.domain.models import Course


class CourseTitleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        if len(normalized) > 120:
            raise ValueError("title must be at most 120 characters")
        return normalized


class CreateCourseRequest(CourseTitleRequest):
    pass


class UpdateCourseRequest(CourseTitleRequest):
    pass


class CourseResponse(BaseModel):
    id: UUID
    educational_environment_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_course(cls, course: Course) -> "CourseResponse":
        return cls(
            id=course.id,
            educational_environment_id=course.educational_environment_id,
            title=course.title,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
