"""Learning-owned enrollment domain model."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class EnrollmentStatus(StrEnum):
    ENROLLED = "enrolled"


@dataclass(frozen=True, slots=True)
class Enrollment:
    id: UUID
    student_user_id: UUID
    course_id: UUID
    status: EnrollmentStatus
    created_at: datetime

    @classmethod
    def create(cls, student_user_id: UUID, course_id: UUID) -> "Enrollment":
        return cls(
            id=uuid4(),
            student_user_id=student_user_id,
            course_id=course_id,
            status=EnrollmentStatus.ENROLLED,
            created_at=datetime.now(UTC),
        )
