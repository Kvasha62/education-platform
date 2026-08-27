from uuid import UUID

from app.assessment.application.attempts import (
    AssessmentAttemptDetail,
    AssessmentAttemptDetailService,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptService,
)
from app.assessment.domain.attempts import (
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
)
from app.education.application.activity_publication import PublishedActivityLookup
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.application.progress import EnrollmentVerifier
from app.learning.domain.models import EnrollmentStatus


class AssessmentAttemptAuthorizationError(Exception):
    pass


class AssessmentAttemptMutationForbiddenError(Exception):
    pass


class StudentAssessmentAttemptService:
    def __init__(
        self,
        activities: PublishedActivityLookup,
        enrollments: EnrollmentVerifier,
        attempts: AssessmentAttemptService,
        attempt_details: AssessmentAttemptDetailService,
    ):
        self.activities = activities
        self.enrollments = enrollments
        self.attempts = attempts
        self.attempt_details = attempt_details

    def _published_activity(self, activity_id: UUID):
        try:
            return self.activities.require_published(activity_id)
        except PublishedActivityNotFoundError as error:
            raise AssessmentAttemptAuthorizationError from error

    def _require_enrollment(self, student_id: UUID, course_id: UUID) -> None:
        if (
            self.enrollments.get_status(student_id, course_id)
            is not EnrollmentStatus.ENROLLED
        ):
            raise AssessmentAttemptMutationForbiddenError

    def _authorize_create(self, student_id: UUID, activity_id: UUID) -> None:
        activity = self._published_activity(activity_id)
        self._require_enrollment(student_id, activity.course_id)

    def _authorize_owned_draft(
        self, student_id: UUID, activity_id: UUID
    ) -> None:
        try:
            activity = self.activities.require_published(activity_id)
        except PublishedActivityNotFoundError as error:
            raise AssessmentAttemptMutationForbiddenError from error
        self._require_enrollment(student_id, activity.course_id)

    def create(
        self,
        student_id: UUID,
        activity_id: UUID,
        definition_id: UUID,
        submission: str | None,
    ) -> AssessmentAttemptDetail:
        self._authorize_create(student_id, activity_id)
        attempt = self.attempts.create(
            definition_id, activity_id, student_id, submission
        )
        return self.attempt_details.from_attempt(attempt)

    def update_submission(
        self,
        student_id: UUID,
        attempt_id: UUID,
        submission: str | None,
    ) -> AssessmentAttemptDetail:
        context = self._existing(
            lambda: self.attempts.resolve_owned(attempt_id, student_id)
        )
        if context.attempt.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        self._authorize_owned_draft(student_id, context.activity_id)
        updated = self.attempts.update_submission(
            context.attempt.id,
            context.attempt.assessment_definition_id,
            context.activity_id,
            student_id,
            submission,
        )
        return self.attempt_details.from_attempt(updated)

    def submit(
        self, student_id: UUID, attempt_id: UUID
    ) -> AssessmentAttemptDetail:
        context = self._existing(
            lambda: self.attempts.resolve_owned(attempt_id, student_id)
        )
        if context.attempt.status is not AssessmentAttemptStatus.DRAFT:
            raise AssessmentAttemptImmutableError
        self._authorize_owned_draft(student_id, context.activity_id)
        submitted = self.attempts.submit(
            context.attempt.id,
            context.attempt.assessment_definition_id,
            context.activity_id,
            student_id,
        )
        return self.attempt_details.from_attempt(submitted)

    def get(
        self, student_id: UUID, attempt_id: UUID
    ) -> AssessmentAttemptDetail:
        context = self._existing(
            lambda: self.attempt_details.get_owned(attempt_id, student_id)
        )
        if context.detail.status is AssessmentAttemptStatus.DRAFT:
            self._authorize_owned_draft(student_id, context.activity_id)
        return context.detail

    @staticmethod
    def _existing(action):
        try:
            return action()
        except AssessmentAttemptNotFoundError as error:
            raise AssessmentAttemptAuthorizationError from error
