"""Education dependency wiring for consuming user-space APIs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.education.application.services import CourseService, EducationalEnvironmentService
from app.education.infrastructure.repositories import (
    SqlAlchemyCourseRepository,
    SqlAlchemyEnvironmentRepository,
)


def get_environment_service(
    db: Annotated[Session, Depends(get_db)],
) -> EducationalEnvironmentService:
    return EducationalEnvironmentService(SqlAlchemyEnvironmentRepository(db))



def get_course_service(
    db: Annotated[Session, Depends(get_db)],
) -> CourseService:
    return CourseService(SqlAlchemyCourseRepository(db))
