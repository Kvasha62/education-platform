"""Student-facing orchestration over Education public application contracts."""

from uuid import UUID

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
