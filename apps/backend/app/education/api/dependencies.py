"""Education dependency wiring for consuming user-space APIs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.education.application.course_publication import CoursePublicationService
from app.education.application.ports import ActivityContentLinkRepository
from app.education.application.services import (
    ActivityService,
    CourseService,
    EducationalEnvironmentService,
    LearningUnitService,
    SectionService,
)
from app.education.infrastructure.content_links import (
    SqlAlchemyActivityContentLinkRepository,
)
from app.education.infrastructure.repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEnvironmentRepository,
    SqlAlchemyLearningUnitRepository,
    SqlAlchemySectionRepository,
)


def get_environment_service(
    db: Annotated[Session, Depends(get_db)],
) -> EducationalEnvironmentService:
    return EducationalEnvironmentService(SqlAlchemyEnvironmentRepository(db))


def get_course_service(
    db: Annotated[Session, Depends(get_db)],
) -> CourseService:
    return CourseService(SqlAlchemyCourseRepository(db))


def get_section_service(
    db: Annotated[Session, Depends(get_db)],
) -> SectionService:
    return SectionService(SqlAlchemySectionRepository(db))


def get_learning_unit_service(
    db: Annotated[Session, Depends(get_db)],
) -> LearningUnitService:
    return LearningUnitService(SqlAlchemyLearningUnitRepository(db))


def get_activity_service(db: Annotated[Session, Depends(get_db)]) -> ActivityService:
    return ActivityService(SqlAlchemyActivityRepository(db))


def get_course_publication_service(
    courses: Annotated[CourseService, Depends(get_course_service)],
    sections: Annotated[SectionService, Depends(get_section_service)],
    units: Annotated[LearningUnitService, Depends(get_learning_unit_service)],
    activities: Annotated[ActivityService, Depends(get_activity_service)],
) -> CoursePublicationService:
    return CoursePublicationService(courses, sections, units, activities)


def get_activity_content_link_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ActivityContentLinkRepository:
    return SqlAlchemyActivityContentLinkRepository(db)
