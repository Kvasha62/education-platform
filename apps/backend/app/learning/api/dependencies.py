"""Learning application composition for Student-facing APIs."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.education.application.activity_publication import (
    PublishedActivityCollectionLookup,
    PublishedActivityLookup,
)
from app.education.application.publication import PublishedCourseLookup
from app.education.composition import (
    get_published_activity_collection_lookup,
    get_published_activity_lookup,
    get_published_course_lookup,
)
from app.learning.application.dashboard import ContinueLearningReader, ContinueLearningService
from app.learning.application.enrollment_read import (
    StudentEnrollmentReader,
    StudentEnrollmentReadService,
)
from app.learning.application.progress import ActivityProgressService
from app.learning.application.services import EnrollmentService
from app.learning.infrastructure.progress import (
    SqlAlchemyEnrollmentVerifier,
    SqlAlchemyProgressRepository,
)
from app.learning.infrastructure.repositories import SqlAlchemyEnrollmentRepository


def get_enrollment_service(
    db: Annotated[Session, Depends(get_db)],
    published_courses: Annotated[PublishedCourseLookup, Depends(get_published_course_lookup)],
) -> EnrollmentService:
    return EnrollmentService(SqlAlchemyEnrollmentRepository(db), published_courses)


def get_student_enrollment_reader(
    db: Annotated[Session, Depends(get_db)],
) -> StudentEnrollmentReader:
    return StudentEnrollmentReadService(SqlAlchemyEnrollmentRepository(db))


def get_activity_progress_service(
    db: Annotated[Session, Depends(get_db)],
    activities: Annotated["PublishedActivityLookup", Depends(get_published_activity_lookup)],
) -> "ActivityProgressService":
    return ActivityProgressService(
        SqlAlchemyProgressRepository(db),
        SqlAlchemyEnrollmentVerifier(db),
        activities,
    )


def get_continue_learning_reader(
    db: Annotated[Session, Depends(get_db)],
    activities: Annotated[
        PublishedActivityCollectionLookup,
        Depends(get_published_activity_collection_lookup),
    ],
) -> ContinueLearningReader:
    return ContinueLearningService(SqlAlchemyProgressRepository(db), activities)
