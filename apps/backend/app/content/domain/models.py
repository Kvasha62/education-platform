"""Content domain model without framework or persistence dependencies."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.content.domain.body import ContentBody, InvalidContentBodyError


class ContentType(StrEnum):
    ARTICLE = "article"
    RESOURCE = "resource"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class InvalidContentTitleError(ValueError):
    pass


class ContentImmutableError(Exception):
    pass


def normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidContentTitleError
    return normalized


@dataclass(frozen=True, slots=True)
class Content:
    id: UUID
    owner_user_id: UUID
    type: ContentType
    title: str
    status: ContentStatus
    body: ContentBody
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, owner_user_id: UUID, content_type: ContentType, title: str) -> "Content":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            owner_user_id=owner_user_id,
            type=content_type,
            title=normalize_title(title),
            status=ContentStatus.DRAFT,
            body=(
                ContentBody.article_empty()
                if content_type is ContentType.ARTICLE
                else ContentBody.resource_empty()
            ),
            created_at=now,
            updated_at=now,
        )

    def require_mutable(self) -> None:
        if self.status is ContentStatus.PUBLISHED:
            raise ContentImmutableError

    def rename(self, title: str) -> "Content":
        self.require_mutable()
        return replace(self, title=normalize_title(title), updated_at=datetime.now(UTC))

    def replace_body(self, body: ContentBody) -> "Content":
        self.require_mutable()
        expected_kind = "article" if self.type is ContentType.ARTICLE else "resource"
        if body.kind != expected_kind:
            raise InvalidContentBodyError
        return replace(self, body=body, updated_at=datetime.now(UTC))

    def publish(self) -> "Content":
        """Publish valid draft Content; repeated publication is idempotent."""
        if self.status is ContentStatus.PUBLISHED:
            return self
        self.body.require_publishable()
        return replace(
            self,
            status=ContentStatus.PUBLISHED,
            updated_at=datetime.now(UTC),
        )
