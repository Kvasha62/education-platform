"""Education dependency wiring for consuming user-space APIs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.education.application.services import (
    ActivityService,
    CourseService,
    EducationalEnvironmentService,
    LearningUnitService,
    SectionService,
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
