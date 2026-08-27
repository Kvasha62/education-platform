from uuid import UUID

from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_scope import (
    ActivityTeacherSpaceScopeQuery,
    AuthorizationDecision,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService


class AssessmentResultAuthorizationError(Exception):
    pass


class TeacherAssessmentResultService:
    def __init__(
        self,
        teacher_spaces: TeacherSpaceService,
        activity_scope: ActivityTeacherSpaceScopeQuery,
        results: AssessmentResultService,
    ) -> None:
        self.teacher_spaces = teacher_spaces
        self.activity_scope = activity_scope
        self.results = results

    def review(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        attempt_id: UUID,
    ) -> AssessmentResult:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        return self.results.review(attempt_id, definition_id, activity_id)

    def correct(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        attempt_id: UUID,
        result_id: UUID,
    ) -> AssessmentResult:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        return self.results.correct(result_id, attempt_id, definition_id, activity_id)

    def _authorize(self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID) -> None:
        try:
            self.teacher_spaces.get_owned(teacher_space_id, teacher_id)
        except TeacherSpaceNotFoundError as error:
            raise AssessmentResultAuthorizationError from error
        if (
            self.activity_scope.verify_activity_belongs_to_teacher_space(
                activity_id, teacher_space_id
            )
            is AuthorizationDecision.DENIED
        ):
            raise AssessmentResultAuthorizationError
