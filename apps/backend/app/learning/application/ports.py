"""Learning application-owned persistence interfaces."""

from typing import Protocol
from uuid import UUID

from app.learning.domain.models import Enrollment


class EnrollmentRepository(Protocol):
    def get_or_create(self, enrollment: Enrollment) -> tuple[Enrollment, bool]: ...


class EnrollmentReadRepository(Protocol):
    def list_for_student(self, student_user_id: UUID) -> list[Enrollment]: ...
