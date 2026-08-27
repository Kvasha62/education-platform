from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID, uuid4


class AssessmentAttemptStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class AssessmentAttemptImmutableError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AssessmentAttempt:
    id: UUID
    assessment_definition_id: UUID
    student_id: UUID
    submission_data: str | None
    status: AssessmentAttemptStatus

    @classmethod
    def create(cls, definition_id: UUID, student_id: UUID, submission_data: str | None):
        return cls(
            uuid4(), definition_id, student_id, submission_data, AssessmentAttemptStatus.DRAFT
        )

    def update_submission(self, submission_data: str | None):
        if self.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        return replace(self, submission_data=submission_data)

    def submit(self):
        if self.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        return replace(self, status=AssessmentAttemptStatus.SUBMITTED)

    def review(self):
        if self.status is not AssessmentAttemptStatus.SUBMITTED:
            raise AssessmentAttemptImmutableError
        return replace(self, status=AssessmentAttemptStatus.REVIEWED)
