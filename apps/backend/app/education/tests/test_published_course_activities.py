from uuid import UUID, uuid4

import pytest

from app.education.application.activity_publication import PublishedCourseActivityReadService
from app.education.application.errors import PublishedCourseNotFoundError
from app.education.application.publication import PublishedCourseReference


class Courses:
    def __init__(self, published: bool) -> None:
        self.published = published

    def require_published(self, course_id: UUID) -> PublishedCourseReference:
        if not self.published:
            raise PublishedCourseNotFoundError
        return PublishedCourseReference(course_id)


class Activities:
    def __init__(self, ids: list[UUID]) -> None:
        self.ids = ids
        self.calls = 0

    def list_ids_for_course(self, course_id: UUID) -> list[UUID]:
        self.calls += 1
        return self.ids


def test_published_course_activity_reader_returns_student_visible_scope() -> None:
    ids = [uuid4(), uuid4()]
    activities = Activities(ids)
    reader = PublishedCourseActivityReadService(Courses(True), activities)
    assert reader.list_activity_ids(uuid4()) == ids
    assert activities.calls == 1


def test_published_course_activity_reader_hides_unpublished_course() -> None:
    activities = Activities([uuid4()])
    reader = PublishedCourseActivityReadService(Courses(False), activities)
    with pytest.raises(PublishedCourseNotFoundError):
        reader.list_activity_ids(uuid4())
    assert activities.calls == 0
