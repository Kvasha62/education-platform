from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import CourseNotFoundError
from app.education.application.services import CourseService
from app.education.domain.models import (
    CourseImmutableError,
    CourseStatus,
    InvalidCourseTitleError,
    InvalidCourseTransitionError,
)


class MemoryCourseRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, course):
        self.items[course.id] = course
        return course

    def list_by_environment(self, environment_id):
        return [
            course
            for course in self.items.values()
            if course.educational_environment_id == environment_id
        ]

    def get_by_id(self, course_id):
        return self.items.get(course_id)

    def get_in_environment(self, course_id, environment_id):
        course = self.items.get(course_id)
        return course if course and course.educational_environment_id == environment_id else None

    def update(self, course):
        self.items[course.id] = course
        return course


@pytest.fixture
def service() -> CourseService:
    return CourseService(MemoryCourseRepository())


def test_create_course_in_environment(service: CourseService) -> None:
    environment_id = uuid4()
    course = service.create(environment_id, "  Mathematics  ")
    assert course.educational_environment_id == environment_id
    assert course.title == "Mathematics"
    assert course.status is CourseStatus.DRAFT


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_invalid_title_is_rejected(service: CourseService, title: str) -> None:
    with pytest.raises(InvalidCourseTitleError):
        service.create(uuid4(), title)


def test_multiple_courses_can_share_environment(service: CourseService) -> None:
    environment_id = uuid4()
    service.create(environment_id, "First")
    service.create(environment_id, "Second")
    assert [course.title for course in service.list(environment_id)] == ["First", "Second"]


def test_get_rejects_course_from_another_environment(service: CourseService) -> None:
    course = service.create(uuid4(), "Private")
    with pytest.raises(CourseNotFoundError):
        service.get(course.id, uuid4())


def test_rename_course(service: CourseService) -> None:
    environment_id = uuid4()
    course = service.create(environment_id, "Original")
    updated = service.rename(course.id, environment_id, "Updated")
    assert updated.title == "Updated"
    assert updated.educational_environment_id == environment_id
    assert updated.status is CourseStatus.DRAFT


def test_published_and_archived_course_cannot_be_renamed(service: CourseService) -> None:
    environment_id = uuid4()
    draft = service.create(environment_id, "Course")
    service.publish(draft.id, environment_id)
    with pytest.raises(CourseImmutableError):
        service.rename(draft.id, environment_id, "Published edit")

    service.archive(draft.id, environment_id)
    with pytest.raises(CourseImmutableError):
        service.rename(draft.id, environment_id, "Archived edit")


def test_publish_and_archive_lifecycle(service: CourseService) -> None:
    environment_id = uuid4()
    draft = service.create(environment_id, "Course")

    published = service.publish(draft.id, environment_id)
    archived = service.archive(draft.id, environment_id)

    assert published.status is CourseStatus.PUBLISHED
    assert archived.status is CourseStatus.ARCHIVED


def test_publish_and_archive_are_idempotent(service: CourseService) -> None:
    environment_id = uuid4()
    draft = service.create(environment_id, "Course")
    published = service.publish(draft.id, environment_id)
    published_again = service.publish(draft.id, environment_id)
    archived = service.archive(draft.id, environment_id)
    archived_again = service.archive(draft.id, environment_id)

    assert published_again == published
    assert published_again.updated_at == published.updated_at
    assert archived_again == archived
    assert archived_again.updated_at == archived.updated_at


def test_invalid_course_transitions_are_deterministic(service: CourseService) -> None:
    environment_id = uuid4()
    draft = service.create(environment_id, "Course")
    with pytest.raises(InvalidCourseTransitionError):
        service.archive(draft.id, environment_id)

    service.publish(draft.id, environment_id)
    service.archive(draft.id, environment_id)
    with pytest.raises(InvalidCourseTransitionError):
        service.publish(draft.id, environment_id)
