"""Learning application-owned persistence interfaces."""

from typing import Protocol

from app.learning.domain.models import Enrollment


class EnrollmentRepository(Protocol):
    def get_or_create(self, enrollment: Enrollment) -> tuple[Enrollment, bool]: ...
