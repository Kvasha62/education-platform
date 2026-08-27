"""Teacher Space use cases and ownership authorization."""

from uuid import UUID

from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.ports import TeacherSpaceRepository
from app.teacher_space.domain.models import TeacherSpace


class TeacherSpaceService:
    def __init__(self, repository: TeacherSpaceRepository) -> None:
        self.repository = repository

    def create(self, owner_user_id: UUID, name: str) -> TeacherSpace:
        return self.repository.add(TeacherSpace.create(owner_user_id, name))

    def list_owned(self, owner_user_id: UUID) -> list[TeacherSpace]:
        return self.repository.list_owned(owner_user_id)

    def get_by_id(self, teacher_space_id: UUID) -> TeacherSpace:
        teacher_space = self.repository.get_by_id(teacher_space_id)
        if teacher_space is None:
            raise TeacherSpaceNotFoundError
        return teacher_space

    def get_owned(self, teacher_space_id: UUID, owner_user_id: UUID) -> TeacherSpace:
        teacher_space = self.repository.get_owned(teacher_space_id, owner_user_id)
        if teacher_space is None:
            raise TeacherSpaceNotFoundError
        return teacher_space

    def rename(self, teacher_space_id: UUID, owner_user_id: UUID, name: str) -> TeacherSpace:
        teacher_space = self.get_owned(teacher_space_id, owner_user_id)
        return self.repository.update(teacher_space.rename(name))

    def disable(self, teacher_space_id: UUID, owner_user_id: UUID) -> TeacherSpace:
        teacher_space = self.get_owned(teacher_space_id, owner_user_id)
        return self.repository.update(teacher_space.disable())
