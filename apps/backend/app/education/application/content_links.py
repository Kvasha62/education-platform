"""Activity / Content association use cases."""

from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

from app.content.public import (
    ContentLookup,
    ContentLookupUnavailable,
    ContentReferenceNotFound,
)
from app.education.application.errors import (
    LinkedContentNotFoundError,
    LinkedContentUnavailableError,
)
from app.education.application.ports import ActivityContentLinkRepository
from app.education.application.services import ActivityService
from app.education.domain.content_links import ActivityContentLink

ContentTypeValue = Literal["article", "resource"]
ContentStatusValue = Literal["draft", "published"]


@dataclass(frozen=True, slots=True)
class ResolvedActivityContent:
    link: ActivityContentLink
    type: ContentTypeValue | None
    status: ContentStatusValue | None
    available_for_student: bool

    @property
    def available(self) -> bool:
        return self.type is not None and self.status is not None


class ActivityContentService:
    """Coordinates an already owner-scoped Activity with Content's public interface."""

    def __init__(
        self,
        activities: ActivityService,
        links: ActivityContentLinkRepository,
        content: ContentLookup,
    ) -> None:
        self.activities = activities
        self.links = links
        self.content = content

    def _require_activity(self, activity_id: UUID, unit_id: UUID) -> None:
        self.activities.get(activity_id, unit_id)

    def attach(
        self,
        activity_id: UUID,
        unit_id: UUID,
        content_id: UUID,
        owner_user_id: UUID,
    ) -> ActivityContentLink:
        self._require_activity(activity_id, unit_id)
        try:
            self.content.lookup_owned(content_id, owner_user_id)
        except ContentReferenceNotFound as error:
            raise LinkedContentNotFoundError from error
        except ContentLookupUnavailable as error:
            raise LinkedContentUnavailableError from error
        return self.links.attach(ActivityContentLink(activity_id, content_id))

    def detach(self, activity_id: UUID, unit_id: UUID, content_id: UUID) -> None:
        self._require_activity(activity_id, unit_id)
        self.links.detach(activity_id, content_id)

    def resolve_for_activity(
        self,
        activity_id: UUID,
        unit_id: UUID,
        owner_user_id: UUID,
    ) -> list[ResolvedActivityContent]:
        self._require_activity(activity_id, unit_id)
        resolved: list[ResolvedActivityContent] = []
        for link in self.links.list_for_activity(activity_id):
            try:
                reference = self.content.lookup_owned(link.content_id, owner_user_id)
            except ContentReferenceNotFound:
                resolved.append(ResolvedActivityContent(link, None, None, False))
                continue
            except ContentLookupUnavailable as error:
                raise LinkedContentUnavailableError from error
            resolved.append(
                ResolvedActivityContent(
                    link=link,
                    type=cast(ContentTypeValue, reference.type.value),
                    status=cast(ContentStatusValue, reference.status.value),
                    available_for_student=reference.available_for_student,
                )
            )
        return resolved

    def list_student_available(
        self,
        activity_id: UUID,
        unit_id: UUID,
        owner_user_id: UUID,
    ) -> list[ResolvedActivityContent]:
        return [
            item
            for item in self.resolve_for_activity(activity_id, unit_id, owner_user_id)
            if item.available_for_student
        ]
