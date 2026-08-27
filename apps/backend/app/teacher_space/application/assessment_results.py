from uuid import UUID

from app.assessment.application.attempts import (
    AssessmentAttemptDetail,
    AssessmentAttemptDetailService,
    AssessmentAttemptPage,
    AssessmentAttemptService,
)
from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.attempts import AssessmentAttemptStatus
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_scope import (
    ActivityScopeResolution,
    ActivityTeacherSpaceScopeQuery,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService


class TeacherAssessmentReviewAuthorizationError(Exception):
    pass


class TeacherAssessmentReviewNotFoundError(Exception):
    pass


class TeacherAssessmentReviewConflictError(Exception):
    pass


class TeacherAssessmentReviewService:
    def __init__(
        self,
        teacher_spaces: TeacherSpaceService,
        activity_scope: ActivityTeacherSpaceScopeQuery,
        attempts: AssessmentAttemptService,
        attempt_details: AssessmentAttemptDetailService,
        results: AssessmentResultService,
    ) -> None:
        self.teacher_spaces = teacher_spaces
        self.activity_scope = activity_scope
        self.attempts = attempts
        self.attempt_details = attempt_details
        self.results = results

    def list_attempts(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        *,
        status: AssessmentAttemptStatus | None,
        page: int,
        page_size: int,
    ) -> AssessmentAttemptPage:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        definition = self.attempts.get_definition_by_activity(activity_id)
        if definition is None:
            return AssessmentAttemptPage(items=[], has_next=False)
        return self.attempt_details.list_for_definition(
            definition.id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def get_attempt(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        attempt_id: UUID,
    ) -> AssessmentAttemptDetail:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        definition = self._definition(activity_id)
        return self.attempt_details.get_for_definition(attempt_id, definition.id)

    def review(
        self,
        teacher_id: UUID,
        teacher_space_id: UUID,
        activity_id: UUID,
        attempt_id: UUID,
        score: int,
        max_score: int,
        feedback: str | None = None,
    ) -> AssessmentResult:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        definition = self._definition(activity_id)
        return self.results.review(
            attempt_id,
            definition.id,
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
        attempt_id: UUID,
        result_id: UUID,
        score: int,
        feedback: str | None,
    ) -> AssessmentResult:
        self._authorize(teacher_id, teacher_space_id, activity_id)
        definition = self._definition(activity_id)
        attempt = self.attempts.get_for_definition(attempt_id, definition.id)
        if attempt.status is not AssessmentAttemptStatus.REVIEWED:
            raise TeacherAssessmentReviewConflictError
        return self.results.correct(
            result_id,
            attempt_id,
            definition.id,
            activity_id,
            score,
            feedback,
        )

    def _definition(self, activity_id: UUID):
        definition = self.attempts.get_definition_by_activity(activity_id)
        if definition is None:
            raise TeacherAssessmentReviewNotFoundError
        return definition

    def _authorize(
        self, teacher_id: UUID, teacher_space_id: UUID, activity_id: UUID
    ) -> None:
        try:
            teacher_space = self.teacher_spaces.get_by_id(teacher_space_id)
        except TeacherSpaceNotFoundError as error:
            raise TeacherAssessmentReviewNotFoundError from error
        if teacher_space.owner_user_id != teacher_id:
            raise TeacherAssessmentReviewAuthorizationError
        resolution = self.activity_scope.resolve_activity_scope(
            activity_id, teacher_space_id
        )
        if resolution is ActivityScopeResolution.NOT_FOUND:
            raise TeacherAssessmentReviewNotFoundError
        if resolution is ActivityScopeResolution.OUTSIDE_SCOPE:
            raise TeacherAssessmentReviewAuthorizationError
