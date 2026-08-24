"""Minimal published Activity lookup exposed to other bounded contexts."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.application.errors import PublishedActivityNotFoundError


@dataclass(frozen=True, slots=True)
class PublishedActivityReference:
    id: UUID
    course_id: UUID


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
