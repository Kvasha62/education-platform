"""Content domain model without framework or persistence dependencies."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ContentType(StrEnum):
    ARTICLE = "article"
    RESOURCE = "resource"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class InvalidContentTitleError(ValueError):
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
            created_at=now,
            updated_at=now,
        )

    def rename(self, title: str) -> "Content":
        return replace(self, title=normalize_title(title), updated_at=datetime.now(UTC))
