"""Published Course read model exposed to Student Space."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast
from uuid import UUID

from app.education.application.content_links import ActivityContentService
from app.education.application.errors import CourseNotFoundError, PublishedCourseNotFoundError
from app.education.application.services import (
    ActivityService,
    CourseService,
    LearningUnitService,
    SectionService,
)
from app.education.domain.models import Activity, CourseStatus, LearningUnit, Section

ActivityTypeValue = Literal["lecture", "video", "homework"]
ContentTypeValue = Literal["article", "resource"]
ContentStatusValue = Literal["published"]


@dataclass(frozen=True, slots=True)
class StudentContentReference:
    id: UUID
    type: ContentTypeValue
    status: ContentStatusValue
    available_for_student: bool


@dataclass(frozen=True, slots=True)
class StudentActivity:
    id: UUID
    title: str
    type: ActivityTypeValue
    position: int
    contents: list[StudentContentReference]


@dataclass(frozen=True, slots=True)
class StudentLearningUnit:
    id: UUID
    title: str
    position: int
    activities: list[StudentActivity]


@dataclass(frozen=True, slots=True)
class StudentSection:
    id: UUID
    title: str
    position: int
    units: list[StudentLearningUnit]


@dataclass(frozen=True, slots=True)
class StudentCourse:
    id: UUID
    title: str
    sections: list[StudentSection]


class PublishedCourseReader(Protocol):
    def get_published(self, course_id: UUID) -> StudentCourse: ...


class StudentCourseReadService:
    def __init__(
        self,
        courses: CourseService,
        sections: SectionService,
        units: LearningUnitService,
        activities: ActivityService,
        activity_contents: ActivityContentService,
    ) -> None:
        self.courses = courses
        self.sections = sections
        self.units = units
        self.activities = activities
        self.activity_contents = activity_contents

    def get_published(self, course_id: UUID) -> StudentCourse:
        try:
            course = self.courses.get_by_id(course_id)
        except CourseNotFoundError as error:
            raise PublishedCourseNotFoundError from error
        if course.status is not CourseStatus.PUBLISHED:
            raise PublishedCourseNotFoundError

        sections = [self._section(item) for item in self.sections.list(course.id)]
        return StudentCourse(id=course.id, title=course.title, sections=sections)

    def _section(self, section: Section) -> StudentSection:
        units = [self._unit(item) for item in self.units.list(section.id)]
        return StudentSection(
            id=section.id,
            title=section.title,
            position=section.position,
            units=units,
        )

    def _unit(self, unit: LearningUnit) -> StudentLearningUnit:
        activities = [
            self._activity(item, unit.id) for item in self.activities.list(unit.id)
        ]
        return StudentLearningUnit(
            id=unit.id,
            title=unit.title,
            position=unit.position,
            activities=activities,
        )

    def _activity(self, activity: Activity, unit_id: UUID) -> StudentActivity:
        contents = [
            StudentContentReference(
                id=item.link.content_id,
                type=cast(ContentTypeValue, item.type),
                status=cast(ContentStatusValue, item.status),
                available_for_student=item.available_for_student,
            )
            for item in self.activity_contents.list_student_available(activity.id, unit_id)
        ]
        return StudentActivity(
            id=activity.id,
            title=activity.title,
            type=cast(ActivityTypeValue, activity.type.value),
            position=activity.position,
            contents=contents,
        )
