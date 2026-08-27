from collections.abc import Callable
from contextlib import AbstractContextManager
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


ResultTransaction = Callable[[], AbstractContextManager[object]]


class TeacherAssessmentResultService:
    def __init__(
        self,
        teacher_spaces: TeacherSpaceService,
        activity_scope: ActivityTeacherSpaceScopeQuery,
        results: AssessmentResultService,
        transaction: ResultTransaction,
    ) -> None:
        self.teacher_spaces = teacher_spaces
        self.activity_scope = activity_scope
        self.results = results
        self.transaction = transaction

    def review(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        attempt_id: UUID,
        score: int,
        max_score: int,
        feedback: str | None = None,
    ) -> AssessmentResult:
        with self.transaction():
            self._authorize(teacher_id, teacher_space_id, activity_id)
            return self.results.review(
                attempt_id,
                definition_id,
                activity_id,
                score,
                max_score,
                feedback,
            )

    def correct(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        attempt_id: UUID,
        result_id: UUID,
        score: int,
        feedback: str | None,
    ) -> AssessmentResult:
        with self.transaction():
            self._authorize(teacher_id, teacher_space_id, activity_id)
            return self.results.correct(
                result_id,
                attempt_id,
                definition_id,
                activity_id,
                score,
                feedback,
            )

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
