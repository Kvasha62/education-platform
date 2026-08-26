"""Student-facing orchestration over Education public application contracts."""

from uuid import UUID

from app.education.application.errors import (
    LinkedContentUnavailableError,
    PublishedCourseNotFoundError,
)
from app.education.application.published_course_list import (
    PublishedCourseListReader,
    PublishedCourseSummary,
)
from app.education.application.student_course import PublishedCourseReader, StudentCourse


class StudentCourseNotFoundError(Exception):
    pass


class StudentContentUnavailableError(Exception):
    pass


class StudentCourseService:
    def __init__(self, courses: PublishedCourseReader) -> None:
        self.courses = courses

    def get_published(self, course_id: UUID) -> StudentCourse:
        try:
            return self.courses.get_published(course_id)
        except PublishedCourseNotFoundError as error:
            raise StudentCourseNotFoundError from error
        except LinkedContentUnavailableError as error:
            raise StudentContentUnavailableError from error


class StudentPublishedCourseListService:
    def __init__(self, courses: "PublishedCourseListReader") -> None:
        self.courses = courses

    def list_published(self) -> list["PublishedCourseSummary"]:
        return self.courses.list_published()
