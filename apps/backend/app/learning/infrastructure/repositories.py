"""Learning-owned SQLAlchemy enrollment repository."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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

    def get_or_create(self, enrollment: Enrollment) -> tuple[Enrollment, bool]:
        model = EnrollmentModel(
            id=enrollment.id,
            student_user_id=enrollment.student_user_id,
            course_id=enrollment.course_id,
            status=enrollment.status,
            created_at=enrollment.created_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError:
            existing = self.db.scalar(
                select(EnrollmentModel).where(
                    EnrollmentModel.student_user_id == enrollment.student_user_id,
                    EnrollmentModel.course_id == enrollment.course_id,
                )
            )
            if existing is None:
                raise
            return _to_domain(existing), False
        return _to_domain(model), True
