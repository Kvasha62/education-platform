"""Canonical Pydantic wire contract for Content Body schema version 1."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


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
