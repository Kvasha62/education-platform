from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import AssessmentAttemptService
from app.education.application.activity_publication import PublishedActivityReference
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.domain.models import EnrollmentStatus
from app.student_space.application.assessment_attempts import (
    AssessmentAttemptAuthorizationError,
    StudentAssessmentAttemptService,
)


class Activities:
    def __init__(self, visible=True):
        self.visible = visible
        self.course = uuid4()

    def require_published(self, activity):
        if not self.visible:
            raise PublishedActivityNotFoundError
        return PublishedActivityReference(activity, self.course, "Activity")


class Enrollments:
    def __init__(self, allowed):
        self.allowed = allowed

    def get_status(self, s, c):
        return EnrollmentStatus.ENROLLED if self.allowed else None


class Attempts:
    def create(self, d, a, s, data):
        return "created"

    def update_submission(self, *args):
        return "updated"

    def submit(self, *args):
        return "submitted"

    def get(self, *args):
        return "read"


@pytest.mark.parametrize("visible,enrolled", [(False, True), (True, False)])
def test_every_student_attempt_operation_requires_visibility_and_enrollment(visible, enrolled):
    service = StudentAssessmentAttemptService(
        Activities(visible), Enrollments(enrolled), cast(AssessmentAttemptService, Attempts())
    )
    student_id, activity_id, definition_id, attempt_id = [uuid4() for _ in range(4)]
    for operation in (
        lambda: service.create(student_id, activity_id, definition_id, None),
        lambda: service.update_submission(student_id, activity_id, definition_id, attempt_id, None),
        lambda: service.submit(student_id, activity_id, definition_id, attempt_id),
        lambda: service.get(student_id, activity_id, definition_id, attempt_id),
    ):
        with pytest.raises(AssessmentAttemptAuthorizationError):
            operation()


def test_authorized_student_operations_are_delegated():
    service = StudentAssessmentAttemptService(
        Activities(), Enrollments(True), cast(AssessmentAttemptService, Attempts())
    )
    s, a, d, i = [uuid4() for _ in range(4)]
    assert (
        service.create(s, a, d, None) == "created"
        and service.update_submission(s, a, d, i, "") == "updated"
        and service.submit(s, a, d, i) == "submitted"
        and service.get(s, a, d, i) == "read"
    )
