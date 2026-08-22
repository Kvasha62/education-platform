from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.content.domain.models import Content, ContentStatus, ContentType


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


class CreateContentRequest(_TitleMixin):
    type: ContentType
    title: str


class UpdateContentRequest(_TitleMixin):
    title: str


class ContentResponse(BaseModel):
    id: UUID
    type: ContentType
    title: str
    status: ContentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_content(cls, content: Content) -> "ContentResponse":
        return cls(
            id=content.id,
            type=content.type,
            title=content.title,
            status=content.status,
            created_at=content.created_at,
            updated_at=content.updated_at,
        )
