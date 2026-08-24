"""Learning application composition for Student-facing APIs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.education.application.publication import PublishedCourseLookup
from app.education.composition import get_published_course_lookup
from app.learning.application.services import EnrollmentService
from app.learning.infrastructure.repositories import SqlAlchemyEnrollmentRepository


def get_enrollment_service(
    db: Annotated[Session, Depends(get_db)],
    published_courses: Annotated[
        PublishedCourseLookup, Depends(get_published_course_lookup)
    ],
) -> EnrollmentService:
    return EnrollmentService(SqlAlchemyEnrollmentRepository(db), published_courses)
