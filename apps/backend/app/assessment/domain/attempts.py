from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID, uuid4


class AssessmentAttemptStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class AssessmentAttemptImmutableError(Exception):
    pass


class InvalidAssessmentSubmissionError(ValueError):
    pass


class AssessmentSubmissionRequiredError(ValueError):
    pass


def normalize_submission(submission: str | None) -> str | None:
    if submission is None:
        return None
    if not isinstance(submission, str):
        raise InvalidAssessmentSubmissionError
    return submission if submission.strip() else None


@dataclass(frozen=True, slots=True)
class AssessmentAttempt:
    id: UUID
    assessment_definition_id: UUID
    student_id: UUID
    submission: str | None
    status: AssessmentAttemptStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "submission", normalize_submission(self.submission))

    @classmethod
    def create(
        cls,
        definition_id: UUID,
        student_id: UUID,
        submission: str | None = None,
    ) -> "AssessmentAttempt":
        return cls(uuid4(), definition_id, student_id, submission, AssessmentAttemptStatus.DRAFT)

    def update_submission(self, submission: str | None) -> "AssessmentAttempt":
        if self.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        return replace(self, submission=normalize_submission(submission))

    def submit(self) -> "AssessmentAttempt":
        if self.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        if self.submission is None:
            raise AssessmentSubmissionRequiredError
        return replace(self, status=AssessmentAttemptStatus.SUBMITTED)

    def review(self) -> "AssessmentAttempt":
        if self.status is not AssessmentAttemptStatus.SUBMITTED:
            raise AssessmentAttemptImmutableError
        return replace(self, status=AssessmentAttemptStatus.REVIEWED)
