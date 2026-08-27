from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr

from app.assessment.application.attempts import AssessmentAttemptDetail
from app.assessment.domain.attempts import AssessmentAttemptStatus
from app.assessment.domain.results import AssessmentResult
from app.content.body_contracts import ContentBodyPayload
from app.education.application.published_course_list import PublishedCourseSummary
from app.education.application.student_content_body import StudentPublishedContentBody
from app.education.application.student_course import (
    ActivityTypeValue,
    ContentStatusValue,
    ContentTypeValue,
    StudentActivity,
    StudentContentReference,
    StudentLearningUnit,
    StudentSection,
)
from app.learning.application.course_progress import CourseProgress
from app.learning.application.enrollment_read import EnrollmentReference
from app.learning.application.progress import ActivityProgressReference
from app.learning.domain.models import Enrollment, EnrollmentStatus
from app.learning.domain.progress import ProgressStatus
from app.student_space.application.dashboard import StudentDashboard
from app.student_space.application.services import StudentCourseAssessmentView


class CreateAssessmentAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission: StrictStr | None = None


class ReplaceAssessmentAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission: StrictStr | None


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


class AssessmentAttemptResponse(BaseModel):
    id: UUID
    assessment_definition_id: UUID
    submission: str | None
    status: AssessmentAttemptStatus
    result: AssessmentResultResponse | None

    @classmethod
    def from_detail(cls, detail: AssessmentAttemptDetail) -> "AssessmentAttemptResponse":
        return cls(
            id=detail.id,
            assessment_definition_id=detail.assessment_definition_id,
            submission=detail.submission,
            status=detail.status,
            result=(
                None
                if detail.result is None
                else AssessmentResultResponse.from_result(detail.result)
            ),
        )


class StudentContentReferenceResponse(BaseModel):
    id: UUID
    type: ContentTypeValue
    status: ContentStatusValue
    available_for_student: bool

    @classmethod
    def from_reference(
        cls, reference: StudentContentReference
    ) -> "StudentContentReferenceResponse":
        return cls(
            id=reference.id,
            type=reference.type,
            status=reference.status,
            available_for_student=reference.available_for_student,
        )


class StudentActivityResponse(BaseModel):
    id: UUID
    title: str
    type: ActivityTypeValue
    position: int
    contents: list[StudentContentReferenceResponse]
    assessment_definition_id: UUID | None

    @classmethod
    def from_activity(
        cls,
        activity: StudentActivity,
        assessment_definition_id: UUID | None,
    ) -> "StudentActivityResponse":
        return cls(
            id=activity.id,
            title=activity.title,
            type=activity.type,
            position=activity.position,
            contents=[
                StudentContentReferenceResponse.from_reference(reference)
                for reference in activity.contents
            ],
            assessment_definition_id=assessment_definition_id,
        )


class StudentLearningUnitResponse(BaseModel):
    id: UUID
    title: str
    position: int
    activities: list[StudentActivityResponse]

    @classmethod
    def from_unit(
        cls,
        unit: StudentLearningUnit,
        assessment_definition_ids: dict[UUID, UUID],
    ) -> "StudentLearningUnitResponse":
        return cls(
            id=unit.id,
            title=unit.title,
            position=unit.position,
            activities=[
                StudentActivityResponse.from_activity(
                    item,
                    assessment_definition_ids.get(item.id),
                )
                for item in unit.activities
            ],
        )


class StudentSectionResponse(BaseModel):
    id: UUID
    title: str
    position: int
    units: list[StudentLearningUnitResponse]

    @classmethod
    def from_section(
        cls,
        section: StudentSection,
        assessment_definition_ids: dict[UUID, UUID],
    ) -> "StudentSectionResponse":
        return cls(
            id=section.id,
            title=section.title,
            position=section.position,
            units=[
                StudentLearningUnitResponse.from_unit(
                    item,
                    assessment_definition_ids,
                )
                for item in section.units
            ],
        )


class StudentCourseResponse(BaseModel):
    id: UUID
    title: str
    sections: list[StudentSectionResponse]

    @classmethod
    def from_course(cls, view: StudentCourseAssessmentView) -> "StudentCourseResponse":
        course = view.course
        return cls(
            id=course.id,
            title=course.title,
            sections=[
                StudentSectionResponse.from_section(
                    item,
                    view.assessment_definition_ids,
                )
                for item in course.sections
            ],
        )


class EnrollmentResponse(BaseModel):
    id: UUID
    course_id: UUID
    status: EnrollmentStatus
    created_at: datetime

    @classmethod
    def from_enrollment(cls, enrollment: Enrollment) -> "EnrollmentResponse":
        return cls(
            id=enrollment.id,
            course_id=enrollment.course_id,
            status=enrollment.status,
            created_at=enrollment.created_at,
        )


class EnrollmentReferenceResponse(BaseModel):
    id: UUID
    course_id: UUID
    status: EnrollmentStatus
    created_at: datetime

    @classmethod
    def from_reference(cls, reference: EnrollmentReference) -> "EnrollmentReferenceResponse":
        return cls(
            id=reference.id,
            course_id=reference.course_id,
            status=reference.status,
            created_at=reference.created_at,
        )


class StudentEnrollmentListResponse(BaseModel):
    items: list[EnrollmentReferenceResponse]


class ActivityProgressResponse(BaseModel):
    activity_id: UUID
    status: "ProgressStatus"

    @classmethod
    def from_reference(cls, reference: "ActivityProgressReference") -> "ActivityProgressResponse":
        return cls(activity_id=reference.activity_id, status=reference.status)


class CourseProgressResponse(BaseModel):
    course_id: UUID
    completed_activities: int
    total_activities: int
    progress_percent: int

    @classmethod
    def from_progress(cls, progress: CourseProgress) -> "CourseProgressResponse":
        return cls(
            course_id=progress.course_id,
            completed_activities=progress.completed_activities,
            total_activities=progress.total_activities,
            progress_percent=progress.progress_percent,
        )


class PublishedCourseSummaryResponse(BaseModel):
    id: UUID
    title: str

    @classmethod
    def from_summary(
        cls, summary: "PublishedCourseSummary"
    ) -> "PublishedCourseSummaryResponse":
        return cls(id=summary.id, title=summary.title)


class PublishedCourseListResponse(BaseModel):
    items: list[PublishedCourseSummaryResponse]


class StudentPublishedContentBodyResponse(BaseModel):
    id: UUID
    type: Literal["article", "resource"]
    body: "ContentBodyPayload"

    @classmethod
    def from_reference(
        cls, reference: StudentPublishedContentBody
    ) -> "StudentPublishedContentBodyResponse":
        return cls(
            id=reference.id,
            type=reference.type,
            body=ContentBodyPayload.model_validate(reference.body),
        )


class DashboardCourseResponse(BaseModel):
    course_id: UUID
    title: str
    status: Literal["enrolled"]
    enrolled_at: datetime


class DashboardContinueLearningResponse(BaseModel):
    course_id: UUID
    activity_id: UUID
    activity_title: str
    status: Literal["in_progress"]
    updated_at: datetime


class StudentDashboardResponse(BaseModel):
    my_courses: list[DashboardCourseResponse]
    continue_learning: DashboardContinueLearningResponse | None

    @classmethod
    def from_dashboard(cls, dashboard: "StudentDashboard") -> "StudentDashboardResponse":
        return cls(
            my_courses=[
                DashboardCourseResponse(
                    course_id=item.course_id,
                    title=item.title,
                    status=item.status,
                    enrolled_at=item.enrolled_at,
                )
                for item in dashboard.my_courses
            ],
            continue_learning=(
                DashboardContinueLearningResponse(
                    course_id=dashboard.continue_learning.course_id,
                    activity_id=dashboard.continue_learning.activity_id,
                    activity_title=dashboard.continue_learning.activity_title,
                    status=dashboard.continue_learning.status,
                    updated_at=dashboard.continue_learning.updated_at,
                )
                if dashboard.continue_learning is not None
                else None
            ),
        )
