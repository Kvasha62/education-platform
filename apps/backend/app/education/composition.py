"""Application composition boundary for cross-context Education use cases."""

from typing import Annotated

from fastapi import Depends

from app.content.api.dependencies import get_content_lookup
from app.content.public import ContentLookup
from app.education.api.dependencies import (
    get_activity_content_link_repository,
    get_activity_service,
)
from app.education.application.content_links import ActivityContentService
from app.education.application.ports import ActivityContentLinkRepository
from app.education.application.services import ActivityService


def get_activity_content_service(
    activities: Annotated[ActivityService, Depends(get_activity_service)],
    links: Annotated[
        ActivityContentLinkRepository,
        Depends(get_activity_content_link_repository),
    ],
    content: Annotated[ContentLookup, Depends(get_content_lookup)],
) -> ActivityContentService:
    return ActivityContentService(activities, links, content)
