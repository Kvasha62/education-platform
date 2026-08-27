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


class DefinitionRepository:
    def __init__(self, definitions):
        self.definitions = definitions

    def get(self, definition_id, activity_id):
        return next(
            (d for d in self.definitions if d.id == definition_id and d.activity_id == activity_id),
            None,
        )

    def get_by_activity(self, activity_id):
        return next((d for d in self.definitions if d.activity_id == activity_id), None)

    def add(self, value):
        return value

    def update(self, value):
        return value


class AttemptRepository:
    def __init__(self):
        self.items = {}

    def add(self, value):
        self.items[value.id] = value
        return value

    def get_owned(self, attempt_id, definition_id, student_id):
        value = self.items.get(attempt_id)
        return (
            value
            if value
            and value.assessment_definition_id == definition_id
            and value.student_id == student_id
            else None
        )

    def update(self, value):
        self.items[value.id] = value
        return value

    def list_owned(self, definition_id, student_id):
        return []


def test_existing_attempt_operations_deny_mismatched_authorized_activity():
    from app.assessment.domain.models import AssessmentDefinition

    student_id, activity_a, activity_b = uuid4(), uuid4(), uuid4()
    definition_a = AssessmentDefinition.create(activity_a, None)
    definition_b = AssessmentDefinition.create(activity_b, None)
    definitions = DefinitionRepository([definition_a, definition_b])
    attempts = AttemptRepository()
    assessment = AssessmentAttemptService(attempts, definitions)
    attempt_a = assessment.create(definition_a.id, activity_a, student_id, "a")
    attempt_b = assessment.create(definition_b.id, activity_b, student_id, "b")
    assert attempt_a.id != attempt_b.id
    student = StudentAssessmentAttemptService(Activities(), Enrollments(True), assessment)

    operations = (
        lambda: student.get(student_id, activity_a, definition_b.id, attempt_b.id),
        lambda: student.update_submission(
            student_id, activity_a, definition_b.id, attempt_b.id, "x"
        ),
        lambda: student.submit(student_id, activity_a, definition_b.id, attempt_b.id),
    )
    for operation in operations:
        with pytest.raises(AssessmentAttemptAuthorizationError):
            operation()

    assert student.get(student_id, activity_a, definition_a.id, attempt_a.id) == attempt_a
