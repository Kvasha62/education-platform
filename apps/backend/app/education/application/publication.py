"""Minimal published Course lookup exposed to other bounded contexts."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.application.errors import CourseNotFoundError, PublishedCourseNotFoundError
from app.education.application.services import CourseService
from app.education.domain.models import CourseStatus


@dataclass(frozen=True, slots=True)
class PublishedCourseReference:
    id: UUID


class PublishedCourseLookup(Protocol):
    def require_published(self, course_id: UUID) -> PublishedCourseReference: ...


class CoursePublicationLookupService:
    def __init__(self, courses: CourseService) -> None:
        self.courses = courses

    def require_published(self, course_id: UUID) -> PublishedCourseReference:
        try:
            course = self.courses.get_by_id(course_id)
        except CourseNotFoundError as error:
            raise PublishedCourseNotFoundError from error
        if course.status is not CourseStatus.PUBLISHED:
            raise PublishedCourseNotFoundError
        return PublishedCourseReference(id=course.id)
