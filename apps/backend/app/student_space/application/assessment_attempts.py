from app.assessment.application.attempts import (
    AssessmentAttemptDetailService,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptService,
)
from app.assessment.domain.attempts import AssessmentAttemptStatus
from app.education.application.activity_publication import PublishedActivityLookup
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.application.progress import EnrollmentVerifier
from app.learning.domain.models import EnrollmentStatus


class AssessmentAttemptAuthorizationError(Exception):
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

    def _authorize_current_access(self, student_id, activity_id):
        try:
            activity = self.activities.require_published(activity_id)
        except PublishedActivityNotFoundError as error:
            raise AssessmentAttemptAuthorizationError from error
        if (
            self.enrollments.get_status(student_id, activity.course_id)
            is not EnrollmentStatus.ENROLLED
        ):
            raise AssessmentAttemptAuthorizationError

    def create(self, student_id, activity_id, definition_id, submission):
        self._authorize_current_access(student_id, activity_id)
        return self.attempts.create(
            definition_id, activity_id, student_id, submission
        )

    def update_submission(
        self,
        student_id,
        activity_id,
        definition_id,
        attempt_id,
        submission,
    ):
        self._authorize_current_access(student_id, activity_id)
        return self._existing(
            lambda: self.attempts.update_submission(
                attempt_id,
                definition_id,
                activity_id,
                student_id,
                submission,
            )
        )

    def submit(self, student_id, activity_id, definition_id, attempt_id):
        self._authorize_current_access(student_id, activity_id)
        return self._existing(
            lambda: self.attempts.submit(
                attempt_id,
                definition_id,
                activity_id,
                student_id,
            )
        )

    def get(self, student_id, activity_id, definition_id, attempt_id):
        detail = self._existing(
            lambda: self.attempt_details.get_owned(
                attempt_id,
                definition_id,
                activity_id,
                student_id,
            )
        )
        if detail.status is AssessmentAttemptStatus.DRAFT:
            self._authorize_current_access(student_id, activity_id)
        return detail

    @staticmethod
    def _existing(action):
        try:
            return action()
        except AssessmentAttemptNotFoundError as error:
            raise AssessmentAttemptAuthorizationError from error
