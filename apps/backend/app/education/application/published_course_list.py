"""Minimal published Course collection contract for Student consumers."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.domain.models import Course


@dataclass(frozen=True, slots=True)
class PublishedCourseSummary:
    id: UUID
    title: str


class PublishedCourseListReader(Protocol):
    def list_published(self) -> list[PublishedCourseSummary]: ...


class PublishedCourseSummaryRepository(Protocol):
    def list_published(self) -> list[Course]: ...


class PublishedCourseListService:
    def __init__(self, courses: PublishedCourseSummaryRepository) -> None:
        self.courses = courses

    def list_published(self) -> list[PublishedCourseSummary]:
        return [
            PublishedCourseSummary(id=course.id, title=course.title)
            for course in self.courses.list_published()
        ]
