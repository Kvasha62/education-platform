from app.assessment.application.attempts import AssessmentAttemptService
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
    ):
        self.activities, self.enrollments, self.attempts = activities, enrollments, attempts

    def _authorize(self, student_id, activity_id):
        try:
            activity = self.activities.require_published(activity_id)
        except PublishedActivityNotFoundError as e:
            raise AssessmentAttemptAuthorizationError from e
        if (
            self.enrollments.get_status(student_id, activity.course_id)
            is not EnrollmentStatus.ENROLLED
        ):
            raise AssessmentAttemptAuthorizationError

    def create(self, sid, aid, did, data):
        self._authorize(sid, aid)
        return self.attempts.create(did, aid, sid, data)

    def update_submission(self, sid, aid, did, attempt_id, data):
        self._authorize(sid, aid)
        return self.attempts.update_submission(attempt_id, did, sid, data)

    def submit(self, sid, aid, did, attempt_id):
        self._authorize(sid, aid)
        return self.attempts.submit(attempt_id, did, sid)

    def get(self, sid, aid, did, attempt_id):
        self._authorize(sid, aid)
        return self.attempts.get(attempt_id, did, sid)
