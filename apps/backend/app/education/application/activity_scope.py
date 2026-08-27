from enum import StrEnum
from typing import Protocol
from uuid import UUID


class AuthorizationDecision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class ActivityTeacherSpaceScopeRepository(Protocol):
    def belongs_to_teacher_space(self, activity_id: UUID, teacher_space_id: UUID) -> bool: ...


class ActivityTeacherSpaceScopeQuery:
    def __init__(self, repository: ActivityTeacherSpaceScopeRepository) -> None:
        self.repository = repository

    def verify_activity_belongs_to_teacher_space(
        self, activity_id: UUID, teacher_space_id: UUID
    ) -> AuthorizationDecision:
        return (
            AuthorizationDecision.ALLOWED
            if self.repository.belongs_to_teacher_space(activity_id, teacher_space_id)
            else AuthorizationDecision.DENIED
        )
