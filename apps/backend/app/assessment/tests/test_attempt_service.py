from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptService,
    AssessmentDefinitionUnavailableError,
)
from app.assessment.domain.attempts import AssessmentSubmissionRequiredError
from app.assessment.domain.models import AssessmentDefinition


class Definitions:
    def __init__(self, definition):
        self.definition = definition

    def get(self, definition_id, activity_id):
        return (
            self.definition
            if self.definition.id == definition_id
            and self.definition.activity_id == activity_id
            else None
        )

    def get_by_activity(self, activity_id):
        return self.definition if self.definition.activity_id == activity_id else None

    def add(self, definition):
        return definition

    def update(self, definition):
        return definition


class Attempts:
    def __init__(self):
        self.items = {}

    def add(self, attempt):
        self.items[attempt.id] = attempt
        return attempt

    def get(self, attempt_id, definition_id):
        attempt = self.items.get(attempt_id)
        return (
            attempt
            if attempt and attempt.assessment_definition_id == definition_id
            else None
        )

    def get_owned(self, attempt_id, definition_id, student_id):
        attempt = self.items.get(attempt_id)
        return (
            attempt
            if attempt
            and attempt.assessment_definition_id == definition_id
            and attempt.student_id == student_id
            else None
        )

    def update(self, attempt):
        self.items[attempt.id] = attempt
        return attempt

    def list_owned(self, definition_id, student_id):
        return [
            attempt
            for attempt in self.items.values()
            if attempt.assessment_definition_id == definition_id
            and attempt.student_id == student_id
        ]


def test_multiple_attempts_and_archived_definition_rules():
    activity_id, student_id = uuid4(), uuid4()
    definition = AssessmentDefinition.create(activity_id, None)
    attempts = Attempts()
    service = AssessmentAttemptService(attempts, Definitions(definition))
    draft = service.create(definition.id, activity_id, student_id, "one")
    second = service.create(definition.id, activity_id, student_id, "two")
    assert draft.id != second.id

    archived = definition.archive()
    archived_service = AssessmentAttemptService(attempts, Definitions(archived))
    with pytest.raises(AssessmentDefinitionUnavailableError):
        archived_service.create(archived.id, activity_id, student_id, None)

    cleared = archived_service.update_submission(
        draft.id,
        archived.id,
        activity_id,
        student_id,
        "   ",
    )
    assert cleared.submission is None
    with pytest.raises(AssessmentSubmissionRequiredError):
        archived_service.submit(draft.id, archived.id, activity_id, student_id)

    edited = archived_service.update_submission(
        draft.id,
        archived.id,
        activity_id,
        student_id,
        "final answer",
    )
    submitted = archived_service.submit(
        edited.id,
        archived.id,
        activity_id,
        student_id,
    )
    assert submitted.status.value == "submitted"
    assert submitted.submission == "final answer"
