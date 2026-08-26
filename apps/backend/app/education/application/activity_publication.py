"""Minimal published Activity lookup exposed to other bounded contexts."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.application.errors import PublishedActivityNotFoundError
from app.education.application.publication import PublishedCourseLookup


@dataclass(frozen=True, slots=True)
class PublishedActivityReference:
    id: UUID
    course_id: UUID
    title: str


class PublishedActivityLookup(Protocol):
    def require_published(self, activity_id: UUID) -> PublishedActivityReference: ...


class PublishedActivityRepository(Protocol):
    def lookup_published(self, activity_id: UUID) -> PublishedActivityReference | None: ...


class ActivityPublicationLookupService:
    def __init__(self, activities: PublishedActivityRepository) -> None:
        self.activities = activities

    def require_published(self, activity_id: UUID) -> PublishedActivityReference:
        reference = self.activities.lookup_published(activity_id)
        if reference is None:
            raise PublishedActivityNotFoundError
        return reference


class PublishedActivityCollectionLookup(Protocol):
    def list_published(
        self, activity_ids: list[UUID], course_ids: set[UUID]
    ) -> dict[UUID, PublishedActivityReference]: ...


class PublishedActivityCollectionLookupService:
    def __init__(self, activities: "PublishedActivityCollectionRepository") -> None:
        self.activities = activities

    def list_published(
        self, activity_ids: list[UUID], course_ids: set[UUID]
    ) -> dict[UUID, PublishedActivityReference]:
        return {
            reference.id: reference
            for reference in self.activities.list_published(activity_ids, course_ids)
        }


class PublishedActivityCollectionRepository(Protocol):
    def list_published(
        self, activity_ids: list[UUID], course_ids: set[UUID]
    ) -> list[PublishedActivityReference]: ...


class PublishedCourseActivityReader(Protocol):
    """Student-visible Activity IDs for one PUBLISHED Course."""

    def list_activity_ids(self, course_id: UUID) -> list[UUID]: ...


class PublishedCourseActivityRepository(Protocol):
    def list_ids_for_course(self, course_id: UUID) -> list[UUID]: ...


class PublishedCourseActivityReadService:
    def __init__(
        self,
        courses: PublishedCourseLookup,
        activities: PublishedCourseActivityRepository,
    ) -> None:
        self.courses = courses
        self.activities = activities

    def list_activity_ids(self, course_id: UUID) -> list[UUID]:
        self.courses.require_published(course_id)
        return self.activities.list_ids_for_course(course_id)
