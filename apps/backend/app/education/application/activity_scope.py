from enum import StrEnum
from typing import Protocol
from uuid import UUID


class AuthorizationDecision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


class ActivityScopeResolution(StrEnum):
    IN_SCOPE = "in_scope"
    OUTSIDE_SCOPE = "outside_scope"
    NOT_FOUND = "not_found"


class ActivityTeacherSpaceScopeRepository(Protocol):
    def belongs_to_teacher_space(self, activity_id: UUID, teacher_space_id: UUID) -> bool: ...
    def resolve_activity_scope(
        self, activity_id: UUID, teacher_space_id: UUID
    ) -> ActivityScopeResolution: ...


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

    def resolve_activity_scope(
        self, activity_id: UUID, teacher_space_id: UUID
    ) -> ActivityScopeResolution:
        return self.repository.resolve_activity_scope(activity_id, teacher_space_id)
