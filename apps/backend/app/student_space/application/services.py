"""Student-facing orchestration over domain-engine application contracts."""

from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.definition_lookup import AssessmentDefinitionIdLookup
from app.education.application.errors import (
    LinkedContentUnavailableError,
    PublishedContentBodyNotFoundError,
    PublishedCourseNotFoundError,
)
from app.education.application.published_course_list import (
    PublishedCourseListReader,
    PublishedCourseSummary,
)
from app.education.application.student_content_body import (
    StudentPublishedContentBody,
    StudentPublishedContentBodyReader,
)
from app.education.application.student_course import PublishedCourseReader, StudentCourse


class StudentCourseNotFoundError(Exception):
    pass


class StudentContentUnavailableError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StudentCourseAssessmentView:
    course: StudentCourse
    assessment_definition_ids: dict[UUID, UUID]


class StudentCourseService:
    def __init__(
        self,
        courses: PublishedCourseReader,
        assessments: AssessmentDefinitionIdLookup,
    ) -> None:
        self.courses = courses
        self.assessments = assessments

    def get_published(self, course_id: UUID) -> StudentCourseAssessmentView:
        try:
            course = self.courses.get_published(course_id)
        except PublishedCourseNotFoundError as error:
            raise StudentCourseNotFoundError from error
        except LinkedContentUnavailableError as error:
            raise StudentContentUnavailableError from error

        definition_ids: dict[UUID, UUID] = {}
        for section in course.sections:
            for unit in section.units:
                for activity in unit.activities:
                    definition_id = self.assessments.get_id_for_activity(activity.id)
                    if definition_id is not None:
                        definition_ids[activity.id] = definition_id
        return StudentCourseAssessmentView(course, definition_ids)


class StudentPublishedCourseListService:
    def __init__(self, courses: "PublishedCourseListReader") -> None:
        self.courses = courses

    def list_published(self) -> list["PublishedCourseSummary"]:
        return self.courses.list_published()


class StudentPublishedContentBodyNotFoundError(Exception):
    pass


class StudentPublishedContentBodyService:
    def __init__(self, content: "StudentPublishedContentBodyReader") -> None:
        self.content = content

    def get_published_body(self, content_id: UUID) -> StudentPublishedContentBody:
        try:
            return self.content.get_published_body(content_id)
        except PublishedContentBodyNotFoundError as error:
            raise StudentPublishedContentBodyNotFoundError from error
        except LinkedContentUnavailableError as error:
            raise StudentContentUnavailableError from error
