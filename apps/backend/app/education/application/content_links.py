"""Activity / Content association use cases."""

from dataclasses import dataclass
from uuid import UUID

from app.content.public import (
    ContentLookup,
    ContentReference,
    ContentReferenceNotFound,
)
from app.education.application.errors import ActivityNotFoundError
from app.education.application.ports import ActivityContentLinkRepository, ActivityRepository
from app.education.domain.content_links import ActivityContentLink


@dataclass(frozen=True, slots=True)
class ResolvedActivityContent:
    link: ActivityContentLink
    reference: ContentReference | None

    @property
    def available(self) -> bool:
        return self.reference is not None


class ActivityContentService:
    """Coordinates an already owner-scoped Activity with Content's public interface."""

    def __init__(
        self,
        activities: ActivityRepository,
        links: ActivityContentLinkRepository,
        content: ContentLookup,
    ) -> None:
        self.activities = activities
        self.links = links
        self.content = content

    def _require_activity(self, activity_id: UUID, unit_id: UUID) -> None:
        if self.activities.get_in_unit(activity_id, unit_id) is None:
            raise ActivityNotFoundError

    def attach(
        self,
        activity_id: UUID,
        unit_id: UUID,
        content_id: UUID,
        owner_user_id: UUID,
    ) -> ActivityContentLink:
        self._require_activity(activity_id, unit_id)
        self.content.lookup_owned(content_id, owner_user_id)
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
                reference = None
            resolved.append(ResolvedActivityContent(link, reference))
        return resolved

    def list_student_available(
        self,
        activity_id: UUID,
        unit_id: UUID,
        owner_user_id: UUID,
    ) -> list[ContentReference]:
        return [
            item.reference
            for item in self.resolve_for_activity(activity_id, unit_id, owner_user_id)
            if item.reference is not None and item.reference.available_for_student
        ]
