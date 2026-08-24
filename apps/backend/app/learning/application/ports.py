"""Learning application-owned persistence interfaces."""

from typing import Protocol
from uuid import UUID

from app.learning.domain.models import Enrollment


class EnrollmentRepository(Protocol):
    def add(self, enrollment: Enrollment) -> Enrollment: ...
    def get_for_student_course(
        self, student_user_id: UUID, course_id: UUID
    ) -> Enrollment | None: ...
