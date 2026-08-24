from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import ActivityNotFoundError
from app.education.application.services import ActivityService
from app.education.domain.models import (
    ActivityType,
    Course,
    CourseImmutableError,
    InvalidActivityPositionError,
    InvalidActivityTitleError,
    InvalidActivityTypeError,
)


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, item):
        self.items[item.id] = item
        return item

    def list_by_unit(self, unit_id):
        return sorted(
            (x for x in self.items.values() if x.learning_unit_id == unit_id),
            key=lambda x: (x.position, x.id),
        )

    def get_in_unit(self, item_id, unit_id):
        item = self.items.get(item_id)
        return item if item and item.learning_unit_id == unit_id else None

    def update(self, item):
        self.items[item.id] = item
        return item

    def delete(self, item):
        self.items.pop(item.id, None)


@pytest.fixture
def service() -> ActivityService:
    return ActivityService(MemoryRepository())


def draft_course() -> Course:
    return Course.create(uuid4(), "Course")


@pytest.mark.parametrize("kind", list(ActivityType))
def test_create_each_type(service: ActivityService, kind: ActivityType) -> None:
    unit_id = uuid4()
    activity = service.create(unit_id, draft_course(), " Activity ", kind, 0)
    assert (activity.learning_unit_id, activity.title, activity.type, activity.position) == (
        unit_id,
        "Activity",
        kind,
        0,
    )


@pytest.mark.parametrize("title", ["", " ", "x" * 121])
def test_invalid_title(service: ActivityService, title: str) -> None:
    with pytest.raises(InvalidActivityTitleError):
        service.create(uuid4(), draft_course(), title, ActivityType.LECTURE, 0)


def test_negative_position(service: ActivityService) -> None:
    with pytest.raises(InvalidActivityPositionError):
        service.create(uuid4(), draft_course(), "A", ActivityType.VIDEO, -1)


def test_invalid_activity_type(service: ActivityService) -> None:
    with pytest.raises(InvalidActivityTypeError):
        service.create(uuid4(), draft_course(), "A", "quiz", 0)  # type: ignore[arg-type]


def test_update_preserves_type(service: ActivityService) -> None:
    unit_id = uuid4()
    course = draft_course()
    item = service.create(unit_id, course, "Old", ActivityType.HOMEWORK, 0)
    changed = service.update(item.id, unit_id, course, title="New", position=10)
    assert (changed.title, changed.position, changed.type) == ("New", 10, ActivityType.HOMEWORK)


def test_order_multiple_and_cross_unit(service: ActivityService) -> None:
    unit_id = uuid4()
    course = draft_course()
    last = service.create(unit_id, course, "Last", ActivityType.VIDEO, 2)
    tied = [
        service.create(unit_id, course, "A", ActivityType.LECTURE, 0),
        service.create(unit_id, course, "B", ActivityType.HOMEWORK, 0),
    ]
    assert service.list(unit_id) == [*sorted(tied, key=lambda x: x.id), last]
    with pytest.raises(ActivityNotFoundError):
        service.get(last.id, uuid4())


def test_delete(service: ActivityService) -> None:
    unit_id = uuid4()
    course = draft_course()
    item = service.create(unit_id, course, "A", ActivityType.LECTURE, 0)
    service.delete(item.id, unit_id, course)
    with pytest.raises(ActivityNotFoundError):
        service.get(item.id, unit_id)


def test_immutable_course_blocks_activity_mutations(service: ActivityService) -> None:
    unit_id = uuid4()
    course = draft_course()
    activity = service.create(unit_id, course, "Activity", ActivityType.LECTURE, 0)
    published = course.publish()

    with pytest.raises(CourseImmutableError):
        service.create(unit_id, published, "Blocked", ActivityType.VIDEO, 1)
    with pytest.raises(CourseImmutableError):
        service.update(activity.id, unit_id, published, title="Blocked", position=None)
    with pytest.raises(CourseImmutableError):
        service.delete(activity.id, unit_id, published)
