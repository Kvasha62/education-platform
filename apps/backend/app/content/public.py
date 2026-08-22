"""Read-only public application interface exposed by Content."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.content.application.ports import ContentRepository
from app.content.domain.models import ContentStatus, ContentType


class ContentReferenceNotFound(Exception):
    pass


class ContentLookupUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ContentReference:
    id: UUID
    type: ContentType
    status: ContentStatus
    available_for_student: bool


class ContentLookup(Protocol):
    def lookup_owned(self, content_id: UUID, owner_user_id: UUID) -> ContentReference: ...


class ContentLookupService:
    """Content-owned implementation that preserves ownership isolation."""

    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    def lookup_owned(self, content_id: UUID, owner_user_id: UUID) -> ContentReference:
        try:
            content = self.repository.get_owned(content_id, owner_user_id)
        except Exception as error:
            raise ContentLookupUnavailable from error
        if content is None:
            raise ContentReferenceNotFound
        return ContentReference(
            id=content.id,
            type=content.type,
            status=content.status,
            available_for_student=content.status is ContentStatus.PUBLISHED,
        )
