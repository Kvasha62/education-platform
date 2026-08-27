from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.assessment.application.attempts import AssessmentAttemptDetail
from app.assessment.domain.attempts import AssessmentAttemptStatus
from app.assessment.domain.results import AssessmentResult


class TeacherAssessmentAttemptStatusFilter(str, Enum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class ReviewAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int
    max_score: int
    feedback: str | None = None


class CorrectAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: UUID
    score: int
    feedback: str | None


class AssessmentResultResponse(BaseModel):
    id: UUID
    attempt_id: UUID
    score: int
    max_score: int
    feedback: str | None

    @classmethod
    def from_result(cls, result: AssessmentResult) -> "AssessmentResultResponse":
        return cls(
            id=result.id,
            attempt_id=result.attempt_id,
            score=result.score,
            max_score=result.max_score,
            feedback=result.feedback,
        )


class TeacherAssessmentAttemptItemResponse(BaseModel):
    id: UUID
    student_id: UUID
    status: AssessmentAttemptStatus
    assessment_definition_id: UUID
    activity_id: UUID
    result: AssessmentResultResponse | None

    @classmethod
    def from_detail(
        cls, detail: AssessmentAttemptDetail, activity_id: UUID
    ) -> "TeacherAssessmentAttemptItemResponse":
        return cls(
            id=detail.id,
            student_id=detail.student_id,
            status=detail.status,
            assessment_definition_id=detail.assessment_definition_id,
            activity_id=activity_id,
            result=(
                None
                if detail.result is None
                else AssessmentResultResponse.from_result(detail.result)
            ),
        )


class TeacherAssessmentAttemptDetailResponse(TeacherAssessmentAttemptItemResponse):
    submission: str | None

    @classmethod
    def from_detail(
        cls, detail: AssessmentAttemptDetail, activity_id: UUID
    ) -> "TeacherAssessmentAttemptDetailResponse":
        return cls(
            id=detail.id,
            student_id=detail.student_id,
            status=detail.status,
            assessment_definition_id=detail.assessment_definition_id,
            activity_id=activity_id,
            submission=detail.submission,
            result=(
                None
                if detail.result is None
                else AssessmentResultResponse.from_result(detail.result)
            ),
        )


class TeacherAssessmentAttemptPageResponse(BaseModel):
    items: list[TeacherAssessmentAttemptItemResponse]
    page: int
    page_size: int
    has_next: bool
