"""Educational Environment use cases."""

from uuid import UUID

from app.education.application.errors import (
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
)
from app.education.application.ports import EnvironmentRepository
from app.education.domain.models import EducationalEnvironment


class EducationalEnvironmentService:
    def __init__(self, repository: EnvironmentRepository) -> None:
        self.repository = repository

    def create(self, teacher_space_id: UUID, name: str) -> EducationalEnvironment:
        if self.repository.get_by_teacher_space(teacher_space_id) is not None:
            raise EnvironmentAlreadyExistsError
        return self.repository.add(EducationalEnvironment.create(teacher_space_id, name))

    def get(self, teacher_space_id: UUID) -> EducationalEnvironment:
        environment = self.repository.get_by_teacher_space(teacher_space_id)
        if environment is None:
            raise EnvironmentNotFoundError
        return environment

    def rename(self, teacher_space_id: UUID, name: str) -> EducationalEnvironment:
        return self.repository.update(self.get(teacher_space_id).rename(name))
