from typing import Any
from uuid import uuid4

import pytest

from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import (
    InvalidTeacherSpaceNameError,
    InvalidTeacherSpaceTransitionError,
    TeacherSpaceDisabledError,
    TeacherSpaceStatus,
)


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, teacher_space):
        self.items[teacher_space.id] = teacher_space
        return teacher_space

    def list_owned(self, owner_user_id):
        return [item for item in self.items.values() if item.owner_user_id == owner_user_id]

    def get_owned(self, teacher_space_id, owner_user_id):
        item = self.items.get(teacher_space_id)
        return item if item and item.owner_user_id == owner_user_id else None

    def update(self, teacher_space):
        self.items[teacher_space.id] = teacher_space
        return teacher_space


@pytest.fixture
def service() -> TeacherSpaceService:
    return TeacherSpaceService(MemoryRepository())


def test_create_active_space_with_owner_and_normalized_name(
    service: TeacherSpaceService,
) -> None:
    owner_id = uuid4()
    teacher_space = service.create(owner_id, "  Mathematics  ")
    assert teacher_space.owner_user_id == owner_id
    assert teacher_space.name == "Mathematics"
    assert teacher_space.status is TeacherSpaceStatus.ACTIVE


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_reject_invalid_name(service: TeacherSpaceService, name: str) -> None:
    with pytest.raises(InvalidTeacherSpaceNameError):
        service.create(uuid4(), name)


def test_owner_can_rename_space(service: TeacherSpaceService) -> None:
    owner_id = uuid4()
    teacher_space = service.create(owner_id, "Original")
    updated = service.rename(teacher_space.id, owner_id, "Updated")
    assert updated.name == "Updated"
    assert updated.owner_user_id == owner_id


def test_non_owner_cannot_resolve_space(service: TeacherSpaceService) -> None:
    teacher_space = service.create(uuid4(), "Private")
    with pytest.raises(TeacherSpaceNotFoundError):
        service.get_owned(teacher_space.id, uuid4())


def test_disabled_space_is_read_only(service: TeacherSpaceService) -> None:
    owner_id = uuid4()
    teacher_space = service.create(owner_id, "Space")
    disabled = service.disable(teacher_space.id, owner_id)
    assert disabled.status is TeacherSpaceStatus.DISABLED
    with pytest.raises(TeacherSpaceDisabledError):
        service.rename(teacher_space.id, owner_id, "No change")
    with pytest.raises(InvalidTeacherSpaceTransitionError):
        service.disable(teacher_space.id, owner_id)
