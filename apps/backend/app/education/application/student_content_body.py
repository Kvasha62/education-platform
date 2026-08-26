"""Student-safe published Content body reader through Education scope."""

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from app.content.public import (
    ContentLookupUnavailable,
    ContentReferenceNotFound,
    PublishedContentBodyLookup,
)
from app.education.application.errors import (
    LinkedContentUnavailableError,
    PublishedContentBodyNotFoundError,
)


@dataclass(frozen=True, slots=True)
class StudentPublishedContentBody:
    id: UUID
    type: Literal["article", "resource"]
    body: dict[str, object]


class PublishedContentAssociationRepository(Protocol):
    def is_linked_to_published_course(self, content_id: UUID) -> bool: ...


class StudentPublishedContentBodyReader(Protocol):
    def get_published_body(self, content_id: UUID) -> StudentPublishedContentBody: ...


class StudentPublishedContentBodyReadService:
    def __init__(
        self,
        associations: PublishedContentAssociationRepository,
        content: PublishedContentBodyLookup,
    ) -> None:
        self.associations = associations
        self.content = content

    def get_published_body(self, content_id: UUID) -> StudentPublishedContentBody:
        if not self.associations.is_linked_to_published_course(content_id):
            raise PublishedContentBodyNotFoundError
        try:
            reference = self.content.read_published_body(content_id)
            return StudentPublishedContentBody(
                id=reference.id,
                type=reference.type.value,
                body=reference.body.to_dict(),
            )
        except ContentReferenceNotFound as error:
            raise PublishedContentBodyNotFoundError from error
        except ContentLookupUnavailable as error:
            raise LinkedContentUnavailableError from error
