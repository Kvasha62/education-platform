from typing import Any
from uuid import uuid4

import pytest

from app.education.application.errors import (
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
)
from app.education.application.services import EducationalEnvironmentService
from app.education.domain.models import InvalidEnvironmentNameError


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, environment):
        self.items[environment.teacher_space_id] = environment
        return environment

    def get_by_teacher_space(self, teacher_space_id):
        return self.items.get(teacher_space_id)

    def update(self, environment):
        self.items[environment.teacher_space_id] = environment
        return environment


@pytest.fixture
def service() -> EducationalEnvironmentService:
    return EducationalEnvironmentService(MemoryRepository())


def test_create_associates_environment_with_teacher_space(
    service: EducationalEnvironmentService,
) -> None:
    teacher_space_id = uuid4()
    environment = service.create(teacher_space_id, "  Learning World  ")
    assert environment.teacher_space_id == teacher_space_id
    assert environment.name == "Learning World"
    assert service.get(teacher_space_id) == environment


@pytest.mark.parametrize("name", ["", "   ", "x" * 121])
def test_invalid_name_is_rejected(
    service: EducationalEnvironmentService, name: str
) -> None:
    with pytest.raises(InvalidEnvironmentNameError):
        service.create(uuid4(), name)


def test_only_one_environment_per_teacher_space(
    service: EducationalEnvironmentService,
) -> None:
    teacher_space_id = uuid4()
    service.create(teacher_space_id, "First")
    with pytest.raises(EnvironmentAlreadyExistsError):
        service.create(teacher_space_id, "Second")


def test_update_name(service: EducationalEnvironmentService) -> None:
    teacher_space_id = uuid4()
    service.create(teacher_space_id, "Original")
    updated = service.rename(teacher_space_id, "Updated")
    assert updated.name == "Updated"
    assert updated.teacher_space_id == teacher_space_id


def test_missing_environment_is_rejected(
    service: EducationalEnvironmentService,
) -> None:
    with pytest.raises(EnvironmentNotFoundError):
        service.get(uuid4())
