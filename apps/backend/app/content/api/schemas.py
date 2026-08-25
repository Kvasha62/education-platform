from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

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


class ContentPageResponse(BaseModel):
    items: list[ContentResponse]
    page: int
    page_size: int
    has_next: bool


class ParagraphBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["paragraph"]
    text: str


class HeadingBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["heading"]
    level: int = Field(ge=1, le=4)
    text: str


class CodeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["code"]
    language: str | None = None
    code: str


class ListBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["list"]
    style: Literal["ordered", "unordered"]
    items: list[str]


class LinkBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["link"]
    url: str
    label: str


ArticleBlock = Annotated[
    ParagraphBlock | HeadingBlock | CodeBlock | ListBlock | LinkBlock,
    Field(discriminator="type"),
]


class ArticleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    kind: Literal["article"]
    blocks: list[ArticleBlock] = Field(max_length=500)


class ResourceBodyValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str | None
    description: str


class ResourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    kind: Literal["resource"]
    resource: ResourceBodyValue


ContentBodyValue = Annotated[ArticleBody | ResourceBody, Field(discriminator="kind")]


class ContentBodyPayload(RootModel[ContentBodyValue]):
    def to_dict(self) -> dict[str, object]:
        return self.root.model_dump(mode="json")
