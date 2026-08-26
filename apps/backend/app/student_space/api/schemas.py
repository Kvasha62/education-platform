from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.content.body_contracts import ContentBodyPayload
from app.education.application.published_course_list import PublishedCourseSummary
from app.education.application.student_content_body import StudentPublishedContentBody
from app.education.application.student_course import (
    ActivityTypeValue,
    ContentStatusValue,
    ContentTypeValue,
    StudentActivity,
    StudentContentReference,
    StudentCourse,
    StudentLearningUnit,
    StudentSection,
)
from app.learning.application.enrollment_read import EnrollmentReference
from app.learning.application.progress import ActivityProgressReference
from app.learning.domain.models import Enrollment, EnrollmentStatus
from app.learning.domain.progress import ProgressStatus


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

    @classmethod
    def from_activity(cls, activity: StudentActivity) -> "StudentActivityResponse":
        return cls(
            id=activity.id,
            title=activity.title,
            type=activity.type,
            position=activity.position,
            contents=[
                StudentContentReferenceResponse.from_reference(reference)
                for reference in activity.contents
            ],
        )


class StudentLearningUnitResponse(BaseModel):
    id: UUID
    title: str
    position: int
    activities: list[StudentActivityResponse]

    @classmethod
    def from_unit(cls, unit: StudentLearningUnit) -> "StudentLearningUnitResponse":
        return cls(
            id=unit.id,
            title=unit.title,
            position=unit.position,
            activities=[StudentActivityResponse.from_activity(item) for item in unit.activities],
        )


class StudentSectionResponse(BaseModel):
    id: UUID
    title: str
    position: int
    units: list[StudentLearningUnitResponse]

    @classmethod
    def from_section(cls, section: StudentSection) -> "StudentSectionResponse":
        return cls(
            id=section.id,
            title=section.title,
            position=section.position,
            units=[StudentLearningUnitResponse.from_unit(item) for item in section.units],
        )


class StudentCourseResponse(BaseModel):
    id: UUID
    title: str
    sections: list[StudentSectionResponse]

    @classmethod
    def from_course(cls, course: StudentCourse) -> "StudentCourseResponse":
        return cls(
            id=course.id,
            title=course.title,
            sections=[StudentSectionResponse.from_section(item) for item in course.sections],
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
