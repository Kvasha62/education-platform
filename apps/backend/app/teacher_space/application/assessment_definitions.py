from uuid import UUID

from app.assessment.application.services import AssessmentDefinitionService
from app.assessment.domain.models import AssessmentDefinition
from app.education.application.activity_scope import (
    ActivityTeacherSpaceScopeQuery,
    AuthorizationDecision,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService


class AssessmentDefinitionAuthorizationError(Exception):
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

    def _authorize(self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID) -> None:
        try:
            self.teacher_spaces.get_owned(teacher_space_id, teacher_id)
        except TeacherSpaceNotFoundError as error:
            raise AssessmentDefinitionAuthorizationError from error
        if (
            self.activity_scope.verify_activity_belongs_to_teacher_space(
                activity_id, teacher_space_id
            )
            is AuthorizationDecision.DENIED
        ):
            raise AssessmentDefinitionAuthorizationError

    def create(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID, instructions: str | None
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        return self.definitions.create(activity_id, instructions)

    def update_instructions(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        instructions: str | None,
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        return self.definitions.update_instructions(definition_id, activity_id, instructions)

    def archive(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID, definition_id: UUID
    ) -> AssessmentDefinition:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        return self.definitions.archive(definition_id, activity_id)
