from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import SectionNotFoundError
from app.education.application.services import SectionService
from app.education.domain.models import (
    InvalidSectionPositionError,
    InvalidSectionTitleError,
)


class MemorySectionRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, section):
        self.items[section.id] = section
        return section

    def list_by_course(self, course_id):
        return sorted(
            (section for section in self.items.values() if section.course_id == course_id),
            key=lambda section: (section.position, section.id),
        )

    def get_in_course(self, section_id, course_id):
        section = self.items.get(section_id)
        return section if section and section.course_id == course_id else None

    def update(self, section):
        self.items[section.id] = section
        return section

    def delete(self, section):
        self.items.pop(section.id, None)


@pytest.fixture
def service() -> SectionService:
    return SectionService(MemorySectionRepository())


def test_create_section_in_course(service: SectionService) -> None:
    course_id = uuid4()
    section = service.create(course_id, "  Introduction  ", 0)
    assert section.course_id == course_id
    assert section.title == "Introduction"
    assert section.position == 0


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_invalid_title_is_rejected(service: SectionService, title: str) -> None:
    with pytest.raises(InvalidSectionTitleError):
        service.create(uuid4(), title, 0)


def test_negative_position_is_rejected(service: SectionService) -> None:
    with pytest.raises(InvalidSectionPositionError):
        service.create(uuid4(), "Section", -1)


def test_list_orders_by_position_then_id(service: SectionService) -> None:
    course_id = uuid4()
    last = service.create(course_id, "Last", 2)
    first_b = service.create(course_id, "First B", 0)
    first_a = service.create(course_id, "First A", 0)

    expected_first = sorted([first_a, first_b], key=lambda section: section.id)
    assert service.list(course_id) == [*expected_first, last]


def test_partial_update_title_and_position(service: SectionService) -> None:
    course_id = uuid4()
    section = service.create(course_id, "Original", 0)
    renamed = service.update(section.id, course_id, title="Updated", position=None)
    moved = service.update(section.id, course_id, title=None, position=3)
    assert renamed.title == "Updated"
    assert renamed.position == 0
    assert moved.title == "Updated"
    assert moved.position == 3


def test_cross_course_access_is_not_found(service: SectionService) -> None:
    section = service.create(uuid4(), "Private", 0)
    with pytest.raises(SectionNotFoundError):
        service.get(section.id, uuid4())


def test_delete_section(service: SectionService) -> None:
    course_id = uuid4()
    section = service.create(course_id, "Temporary", 0)
    service.delete(section.id, course_id)
    with pytest.raises(SectionNotFoundError):
        service.get(section.id, course_id)
