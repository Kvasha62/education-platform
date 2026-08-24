"""Learning-owned SQLAlchemy enrollment repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.learning.domain.models import Enrollment
from app.learning.infrastructure.models import EnrollmentModel


def _to_domain(model: EnrollmentModel) -> Enrollment:
    return Enrollment(
        id=model.id,
        student_user_id=model.student_user_id,
        course_id=model.course_id,
        status=model.status,
        created_at=model.created_at,
    )


class SqlAlchemyEnrollmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, enrollment: Enrollment) -> Enrollment:
        model = EnrollmentModel(
            id=enrollment.id,
            student_user_id=enrollment.student_user_id,
            course_id=enrollment.course_id,
            status=enrollment.status,
            created_at=enrollment.created_at,
        )
        self.db.add(model)
        self.db.flush()
        return _to_domain(model)

    def get_for_student_course(
        self, student_user_id: UUID, course_id: UUID
    ) -> Enrollment | None:
        model = self.db.scalar(
            select(EnrollmentModel).where(
                EnrollmentModel.student_user_id == student_user_id,
                EnrollmentModel.course_id == course_id,
            )
        )
        return _to_domain(model) if model else None
