from uuid import UUID, uuid4

import pytest

from app.education.application.errors import PublishedCourseNotFoundError
from app.education.application.publication import CoursePublicationLookupService
from app.education.application.services import CourseService
from app.education.domain.models import Course


class CourseRepository:
    def __init__(self, course: Course | None) -> None:
        self.course = course

    def get_by_id(self, course_id: UUID) -> Course | None:
        return self.course if self.course and self.course.id == course_id else None

    def add(self, course: Course) -> Course:
        raise NotImplementedError

    def list_by_environment(self, environment_id: UUID) -> list[Course]:
        raise NotImplementedError

    def get_in_environment(
        self, course_id: UUID, environment_id: UUID
    ) -> Course | None:
        raise NotImplementedError

    def update(self, course: Course) -> Course:
        raise NotImplementedError


def test_lookup_returns_only_reference_for_published_course() -> None:
    course = Course.create(uuid4(), "Course").publish()
    reference = CoursePublicationLookupService(CourseService(CourseRepository(course))).require_published(
        course.id
    )
    assert reference.id == course.id
    assert set(reference.__slots__) == {"id"}


@pytest.mark.parametrize("course", [None, Course.create(uuid4(), "Draft")])
def test_lookup_hides_missing_and_non_published_course(course: Course | None) -> None:
    lookup = CoursePublicationLookupService(CourseService(CourseRepository(course)))
    with pytest.raises(PublishedCourseNotFoundError):
        lookup.require_published(course.id if course else uuid4())


def test_lookup_hides_archived_course() -> None:
    course = Course.create(uuid4(), "Course").publish().archive()
    lookup = CoursePublicationLookupService(CourseService(CourseRepository(course)))
    with pytest.raises(PublishedCourseNotFoundError):
        lookup.require_published(course.id)
