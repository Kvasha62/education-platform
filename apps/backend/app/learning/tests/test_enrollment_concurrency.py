"""Persistence regression coverage for concurrent idempotent enrollment."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.learning.domain.models import Enrollment
from app.learning.infrastructure.models import EnrollmentModel
from app.learning.infrastructure.repositories import SqlAlchemyEnrollmentRepository


def test_concurrent_duplicate_enrollment_returns_one_created_and_one_existing(
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'enrollment.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    student_user_id, course_id = uuid4(), uuid4()
    ready = Barrier(2)

    def enroll() -> tuple[Enrollment, bool]:
        with factory() as session:
            repository = SqlAlchemyEnrollmentRepository(session)
            ready.wait()
            result = repository.get_or_create(
                Enrollment.create(student_user_id, course_id)
            )
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(enroll)
        second = executor.submit(enroll)
        results = [first.result(), second.result()]

    assert sorted(created for _, created in results) == [False, True]
    assert results[0][0].id == results[1][0].id
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(EnrollmentModel)) == 1
