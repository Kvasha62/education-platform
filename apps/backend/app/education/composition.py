"""Application composition boundary for cross-context Education use cases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.content.api.dependencies import get_content_lookup
from app.content.public import ContentLookup
from app.core.database import get_db
from app.education.api.dependencies import (
    get_activity_content_link_repository,
    get_activity_service,
    get_course_service,
    get_learning_unit_service,
    get_section_service,
)
from app.education.application.activity_publication import (
    ActivityPublicationLookupService,
    PublishedActivityLookup,
)
from app.education.application.content_links import ActivityContentService
from app.education.application.ports import ActivityContentLinkRepository
from app.education.application.publication import (
    CoursePublicationLookupService,
    PublishedCourseLookup,
)
from app.education.application.services import (
    ActivityService,
    CourseService,
    LearningUnitService,
    SectionService,
)
from app.education.application.student_course import (
    PublishedCourseReader,
    StudentCourseReadService,
)
from app.education.infrastructure.activity_publication import (
    SqlAlchemyPublishedActivityRepository,
)


def get_activity_content_service(
    activities: Annotated[ActivityService, Depends(get_activity_service)],
    links: Annotated[
        ActivityContentLinkRepository,
        Depends(get_activity_content_link_repository),
    ],
    content: Annotated[ContentLookup, Depends(get_content_lookup)],
) -> ActivityContentService:
    return ActivityContentService(activities, links, content)


def get_published_course_reader(
    courses: Annotated[CourseService, Depends(get_course_service)],
    sections: Annotated[SectionService, Depends(get_section_service)],
    units: Annotated[LearningUnitService, Depends(get_learning_unit_service)],
    activities: Annotated[ActivityService, Depends(get_activity_service)],
    activity_contents: Annotated[
        ActivityContentService,
        Depends(get_activity_content_service),
    ],
) -> PublishedCourseReader:
    return StudentCourseReadService(
        courses,
        sections,
        units,
        activities,
        activity_contents,
    )


def get_published_course_lookup(
    courses: Annotated[CourseService, Depends(get_course_service)],
) -> "PublishedCourseLookup":
    return CoursePublicationLookupService(courses)


def get_published_activity_lookup(
    db: Annotated[Session, Depends(get_db)],
) -> PublishedActivityLookup:
    return ActivityPublicationLookupService(SqlAlchemyPublishedActivityRepository(db))
