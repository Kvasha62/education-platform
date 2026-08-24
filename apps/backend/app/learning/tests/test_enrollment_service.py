from uuid import UUID, uuid4

import pytest

from app.education.application.errors import PublishedCourseNotFoundError
from app.education.application.publication import PublishedCourseReference
from app.learning.application.services import EnrollmentCourseNotFoundError, EnrollmentService
from app.learning.domain.models import Enrollment


class FakeCourses:
    def __init__(self, published: bool = True) -> None:
        self.published = published
        self.calls: list[UUID] = []

    def require_published(self, course_id: UUID) -> PublishedCourseReference:
        self.calls.append(course_id)
        if not self.published:
            raise PublishedCourseNotFoundError
        return PublishedCourseReference(course_id)


class FakeEnrollments:
    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, UUID], Enrollment] = {}

    def add(self, enrollment: Enrollment) -> Enrollment:
        key = (enrollment.student_user_id, enrollment.course_id)
        assert key not in self.rows
        self.rows[key] = enrollment
        return enrollment

    def get_for_student_course(
        self, student_user_id: UUID, course_id: UUID
    ) -> Enrollment | None:
        return self.rows.get((student_user_id, course_id))


def test_enroll_uses_minimal_publication_lookup_and_is_idempotent() -> None:
    student_id, course_id = uuid4(), uuid4()
    courses, repository = FakeCourses(), FakeEnrollments()
    service = EnrollmentService(repository, courses)

    first = service.enroll(student_id, course_id)
    repeated = service.enroll(student_id, course_id)

    assert first.created is True
    assert repeated.created is False
    assert repeated.enrollment == first.enrollment
    assert courses.calls == [course_id, course_id]
    assert len(repository.rows) == 1


def test_unpublished_course_is_hidden_and_creates_nothing() -> None:
    repository = FakeEnrollments()
    service = EnrollmentService(repository, FakeCourses(published=False))

    with pytest.raises(EnrollmentCourseNotFoundError):
        service.enroll(uuid4(), uuid4())
    assert repository.rows == {}
