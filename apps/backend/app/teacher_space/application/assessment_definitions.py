from uuid import UUID

from app.assessment.application.services import AssessmentDefinitionService
from app.assessment.domain.models import AssessmentDefinition
from app.education.application.activity_scope import (
    ActivityScopeResolution,
    ActivityTeacherSpaceScopeQuery,
)
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpaceDisabledError, TeacherSpaceStatus


class AssessmentDefinitionAuthorizationError(Exception):
    pass


class TeacherAssessmentDefinitionActivityNotFoundError(Exception):
    pass


class TeacherAssessmentDefinitionService:
    def __init__(
        self,
        teacher_spaces: TeacherSpaceService,
        activity_scope: ActivityTeacherSpaceScopeQuery,
        definitions: AssessmentDefinitionService,
    ) -> None:
        self.teacher_spaces, self.activity_scope, self.definitions = (
            teacher_spaces,
            activity_scope,
            definitions,
        )

    def _authorize(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        *,
        write: bool,
    ) -> None:
        teacher_space = self.teacher_spaces.get_by_id(teacher_space_id)
        if teacher_space.owner_user_id != teacher_id:
            raise AssessmentDefinitionAuthorizationError
        if write and teacher_space.status is TeacherSpaceStatus.DISABLED:
            raise TeacherSpaceDisabledError
        resolution = self.activity_scope.resolve_activity_scope(
            activity_id, teacher_space_id
        )
        if resolution is ActivityScopeResolution.NOT_FOUND:
            raise TeacherAssessmentDefinitionActivityNotFoundError
        if resolution is ActivityScopeResolution.OUTSIDE_SCOPE:
            raise AssessmentDefinitionAuthorizationError

    def get(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id, write=False)
        return self.definitions.get(activity_id)

    def create(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID, instructions: str | None
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id, write=True)
        return self.definitions.create(activity_id, instructions)

    def update_instructions(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        instructions: str | None,
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id, write=True)
        definition = self.definitions.get(activity_id)
        return self.definitions.update_instructions(definition.id, activity_id, instructions)

    def archive(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id, write=True)
        definition = self.definitions.get(activity_id)
        return self.definitions.archive(definition.id, activity_id)
