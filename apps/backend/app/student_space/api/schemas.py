from uuid import UUID

from pydantic import BaseModel

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
