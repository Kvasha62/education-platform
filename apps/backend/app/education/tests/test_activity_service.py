from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import ActivityNotFoundError
from app.education.application.services import ActivityService
from app.education.domain.models import (
    ActivityType,
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


@pytest.mark.parametrize("kind", list(ActivityType))
def test_create_each_type(service: ActivityService, kind: ActivityType) -> None:
    unit_id = uuid4()
    activity = service.create(unit_id, " Activity ", kind, 0)
    assert (activity.learning_unit_id, activity.title, activity.type, activity.position) == (
        unit_id,
        "Activity",
        kind,
        0,
    )


@pytest.mark.parametrize("title", ["", " ", "x" * 121])
def test_invalid_title(service: ActivityService, title: str) -> None:
    with pytest.raises(InvalidActivityTitleError):
        service.create(uuid4(), title, ActivityType.LECTURE, 0)


def test_negative_position(service: ActivityService) -> None:
    with pytest.raises(InvalidActivityPositionError):
        service.create(uuid4(), "A", ActivityType.VIDEO, -1)


def test_invalid_activity_type(service: ActivityService) -> None:
    with pytest.raises(InvalidActivityTypeError):
        service.create(uuid4(), "A", "quiz", 0)  # type: ignore[arg-type]


def test_update_preserves_type(service: ActivityService) -> None:
    unit_id = uuid4()
    item = service.create(unit_id, "Old", ActivityType.HOMEWORK, 0)
    changed = service.update(item.id, unit_id, title="New", position=10)
    assert (changed.title, changed.position, changed.type) == ("New", 10, ActivityType.HOMEWORK)


def test_order_multiple_and_cross_unit(service: ActivityService) -> None:
    unit_id = uuid4()
    last = service.create(unit_id, "Last", ActivityType.VIDEO, 2)
    tied = [
        service.create(unit_id, "A", ActivityType.LECTURE, 0),
        service.create(unit_id, "B", ActivityType.HOMEWORK, 0),
    ]
    assert service.list(unit_id) == [*sorted(tied, key=lambda x: x.id), last]
    with pytest.raises(ActivityNotFoundError):
        service.get(last.id, uuid4())


def test_delete(service: ActivityService) -> None:
    unit_id = uuid4()
    item = service.create(unit_id, "A", ActivityType.LECTURE, 0)
    service.delete(item.id, unit_id)
    with pytest.raises(ActivityNotFoundError):
        service.get(item.id, unit_id)
