from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.learning.application.enrollment_read import StudentEnrollmentReadService
from app.learning.domain.models import EnrollmentStatus
from app.learning.infrastructure.models import EnrollmentModel
from app.learning.infrastructure.repositories import SqlAlchemyEnrollmentRepository


def test_reader_returns_safe_references_in_deterministic_order() -> None:
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    student_id = UUID("00000000-0000-0000-0000-000000000001")
    other_id = UUID("00000000-0000-0000-0000-000000000002")
    created_at = datetime(2026, 8, 25, tzinfo=UTC)
    later_id = UUID("00000000-0000-0000-0000-000000000020")
    earlier_id = UUID("00000000-0000-0000-0000-000000000010")

    with Session(engine) as session:
        session.add_all(
            [
                EnrollmentModel(
                    id=later_id,
                    student_user_id=student_id,
                    course_id=UUID("00000000-0000-0000-0000-000000000102"),
                    status=EnrollmentStatus.ENROLLED,
                    created_at=created_at,
                ),
                EnrollmentModel(
                    id=earlier_id,
                    student_user_id=student_id,
                    course_id=UUID("00000000-0000-0000-0000-000000000101"),
                    status=EnrollmentStatus.ENROLLED,
                    created_at=created_at,
                ),
                EnrollmentModel(
                    id=UUID("00000000-0000-0000-0000-000000000030"),
                    student_user_id=other_id,
                    course_id=UUID("00000000-0000-0000-0000-000000000103"),
                    status=EnrollmentStatus.ENROLLED,
                    created_at=created_at,
                ),
            ]
        )
        session.commit()
        references = StudentEnrollmentReadService(
            SqlAlchemyEnrollmentRepository(session)
        ).list_for_student(student_id)

    assert [reference.id for reference in references] == [earlier_id, later_id]
    assert all(
        set(reference.__slots__) == {"id", "course_id", "status", "created_at"}
        for reference in references
    )
