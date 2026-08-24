"""Learning enrollment application use cases."""

from dataclasses import dataclass
from uuid import UUID

from app.education.application.errors import PublishedCourseNotFoundError
from app.education.application.publication import PublishedCourseLookup
from app.learning.application.ports import EnrollmentRepository
from app.learning.domain.models import Enrollment


class EnrollmentCourseNotFoundError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EnrollmentResult:
    enrollment: Enrollment
    created: bool


class EnrollmentService:
    def __init__(
        self,
        enrollments: EnrollmentRepository,
        published_courses: PublishedCourseLookup,
    ) -> None:
        self.enrollments = enrollments
        self.published_courses = published_courses

    def enroll(self, student_user_id: UUID, course_id: UUID) -> EnrollmentResult:
        try:
            course = self.published_courses.require_published(course_id)
        except PublishedCourseNotFoundError as error:
            raise EnrollmentCourseNotFoundError from error

        existing = self.enrollments.get_for_student_course(student_user_id, course.id)
        if existing is not None:
            return EnrollmentResult(existing, created=False)
        enrollment = self.enrollments.add(Enrollment.create(student_user_id, course.id))
        return EnrollmentResult(enrollment, created=True)
