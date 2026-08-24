"""Safe Learning enrollment read contract for Student Space."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.learning.application.ports import EnrollmentReadRepository
from app.learning.domain.models import EnrollmentStatus


@dataclass(frozen=True, slots=True)
class EnrollmentReference:
    id: UUID
    course_id: UUID
    status: EnrollmentStatus
    created_at: datetime


class StudentEnrollmentReader(Protocol):
    def list_for_student(self, student_user_id: UUID) -> list[EnrollmentReference]: ...


class StudentEnrollmentReadService:
    def __init__(self, enrollments: EnrollmentReadRepository) -> None:
        self.enrollments = enrollments

    def list_for_student(self, student_user_id: UUID) -> list[EnrollmentReference]:
        return [
            EnrollmentReference(
                id=enrollment.id,
                course_id=enrollment.course_id,
                status=enrollment.status,
                created_at=enrollment.created_at,
            )
            for enrollment in self.enrollments.list_for_student(student_user_id)
        ]
