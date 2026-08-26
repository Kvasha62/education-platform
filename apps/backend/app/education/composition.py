"""Application composition boundary for cross-context Education use cases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.content.api.dependencies import (
    get_content_lookup,
    get_published_content_body_lookup,
)
from app.content.public import ContentLookup, PublishedContentBodyLookup
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
    PublishedActivityCollectionLookup,
    PublishedActivityCollectionLookupService,
    PublishedActivityLookup,
    PublishedCourseActivityReader,
    PublishedCourseActivityReadService,
)
from app.education.application.content_links import ActivityContentService
from app.education.application.ports import ActivityContentLinkRepository
from app.education.application.publication import (
    CoursePublicationLookupService,
    PublishedCourseLookup,
)
from app.education.application.published_course_list import (
    PublishedCourseListReader,
    PublishedCourseListService,
)
from app.education.application.services import (
    ActivityService,
    CourseService,
    LearningUnitService,
    SectionService,
)
from app.education.application.student_content_body import (
    StudentPublishedContentBodyReader,
    StudentPublishedContentBodyReadService,
)
from app.education.application.student_course import (
    PublishedCourseReader,
    StudentCourseReadService,
)
from app.education.infrastructure.activity_publication import (
    SqlAlchemyPublishedActivityRepository,
)
from app.education.infrastructure.repositories import SqlAlchemyCourseRepository
from app.education.infrastructure.student_content_body import (
    SqlAlchemyPublishedContentAssociationRepository,
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


def get_published_course_list_reader(
    db: Annotated[Session, Depends(get_db)],
) -> PublishedCourseListReader:
    return PublishedCourseListService(SqlAlchemyCourseRepository(db))


def get_student_published_content_body_reader(
    db: Annotated[Session, Depends(get_db)],
    content: Annotated[
        PublishedContentBodyLookup, Depends(get_published_content_body_lookup)
    ],
) -> StudentPublishedContentBodyReader:
    return StudentPublishedContentBodyReadService(
        SqlAlchemyPublishedContentAssociationRepository(db),
        content,
    )


def get_published_activity_collection_lookup(
    db: Annotated[Session, Depends(get_db)],
) -> PublishedActivityCollectionLookup:
    return PublishedActivityCollectionLookupService(
        SqlAlchemyPublishedActivityRepository(db)
    )


def get_published_course_activity_reader(
    db: Annotated[Session, Depends(get_db)],
    courses: Annotated[PublishedCourseLookup, Depends(get_published_course_lookup)],
) -> PublishedCourseActivityReader:
    return PublishedCourseActivityReadService(
        courses,
        SqlAlchemyPublishedActivityRepository(db),
    )
