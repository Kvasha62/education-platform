from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import LearningUnitNotFoundError
from app.education.application.services import LearningUnitService
from app.education.domain.models import (
    Course,
    CourseImmutableError,
    InvalidLearningUnitPositionError,
    InvalidLearningUnitTitleError,
)


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, unit):
        self.items[unit.id] = unit
        return unit

    def list_by_section(self, section_id):
        return sorted(
            (unit for unit in self.items.values() if unit.section_id == section_id),
            key=lambda unit: (unit.position, unit.id),
        )

    def get_in_section(self, unit_id, section_id):
        unit = self.items.get(unit_id)
        return unit if unit and unit.section_id == section_id else None

    def update(self, unit):
        self.items[unit.id] = unit
        return unit

    def delete(self, unit):
        self.items.pop(unit.id, None)


@pytest.fixture
def service() -> LearningUnitService:
    return LearningUnitService(MemoryRepository())


def draft_course() -> Course:
    return Course.create(uuid4(), "Course")


def test_create_unit_in_section(service: LearningUnitService) -> None:
    section_id = uuid4()
    unit = service.create(section_id, draft_course(), "  Lesson  ", 0)
    assert (unit.section_id, unit.title, unit.position) == (section_id, "Lesson", 0)


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_invalid_title(service: LearningUnitService, title: str) -> None:
    with pytest.raises(InvalidLearningUnitTitleError):
        service.create(uuid4(), draft_course(), title, 0)


def test_negative_position(service: LearningUnitService) -> None:
    with pytest.raises(InvalidLearningUnitPositionError):
        service.create(uuid4(), draft_course(), "Unit", -1)


def test_order_and_duplicate_positions(service: LearningUnitService) -> None:
    section_id = uuid4()
    course = draft_course()
    last = service.create(section_id, course, "Last", 5)
    tied = [
        service.create(section_id, course, "A", 0),
        service.create(section_id, course, "B", 0),
    ]
    assert service.list(section_id) == [*sorted(tied, key=lambda unit: unit.id), last]


def test_partial_updates(service: LearningUnitService) -> None:
    section_id = uuid4()
    course = draft_course()
    unit = service.create(section_id, course, "Original", 0)
    renamed = service.update(unit.id, section_id, course, title="Updated", position=None)
    moved = service.update(unit.id, section_id, course, title=None, position=99)
    assert (renamed.title, renamed.position) == ("Updated", 0)
    assert (moved.title, moved.position) == ("Updated", 99)


def test_cross_section_not_found(service: LearningUnitService) -> None:
    unit = service.create(uuid4(), draft_course(), "Private", 0)
    with pytest.raises(LearningUnitNotFoundError):
        service.get(unit.id, uuid4())


def test_delete(service: LearningUnitService) -> None:
    section_id = uuid4()
    course = draft_course()
    unit = service.create(section_id, course, "Temporary", 0)
    service.delete(unit.id, section_id, course)
    with pytest.raises(LearningUnitNotFoundError):
        service.get(unit.id, section_id)


def test_immutable_course_blocks_learning_unit_mutations(service: LearningUnitService) -> None:
    section_id = uuid4()
    course = draft_course()
    unit = service.create(section_id, course, "Unit", 0)
    published = course.publish()

    with pytest.raises(CourseImmutableError):
        service.create(section_id, published, "Blocked", 1)
    with pytest.raises(CourseImmutableError):
        service.update(unit.id, section_id, published, title="Blocked", position=None)
    with pytest.raises(CourseImmutableError):
        service.delete(unit.id, section_id, published)
