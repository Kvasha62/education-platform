from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptDetailService,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptResultMissingError,
    AssessmentAttemptService,
)
from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.domain.results import AssessmentResult


class Definitions:
    def __init__(self, definition):
        self.definition = definition

    def get(self, definition_id, activity_id):
        return (
            self.definition
            if self.definition
            and self.definition.id == definition_id
            and self.definition.activity_id == activity_id
            else None
        )

    def get_by_id(self, definition_id):
        return (
            self.definition
            if self.definition and self.definition.id == definition_id
            else None
        )


class Attempts:
    def __init__(self, attempt):
        self.attempt = attempt

    def get_owned_by_id(self, attempt_id, student_id):
        return (
            self.attempt
            if self.attempt.id == attempt_id and self.attempt.student_id == student_id
            else None
        )


class Results:
    def __init__(self, result=None):
        self.result = result
        self.read_count = 0

    def get_by_attempt(self, attempt_id):
        self.read_count += 1
        return self.result if self.result and self.result.attempt_id == attempt_id else None


def detail_service(attempt, result=None, include_definition=True):
    definition = AssessmentDefinition.create(uuid4(), None)
    attempt = AssessmentAttempt(
        attempt.id,
        definition.id,
        attempt.student_id,
        attempt.submission,
        attempt.status,
    )
    definitions = Definitions(definition if include_definition else None)
    attempts = Attempts(attempt)
    results = Results(result)
    if result is not None:
        results.result = AssessmentResult(
            result.id,
            attempt.id,
            result.score,
            result.max_score,
            result.feedback,
        )
    attempt_service = AssessmentAttemptService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
    )
    service = AssessmentAttemptDetailService(
        attempt_service,
        cast(AssessmentResultRepository, results),
    )
    return service, definition, attempt, results


@pytest.mark.parametrize("submitted", [False, True])
def test_draft_and_submitted_detail_have_no_result(submitted):
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer")
    if submitted:
        attempt = attempt.submit()
    service, definition, attempt, results = detail_service(attempt)

    context = service.get_owned(attempt.id, attempt.student_id)
    detail = context.detail

    assert context.activity_id == definition.activity_id
    assert detail.id == attempt.id
    assert detail.assessment_definition_id == definition.id
    assert detail.submission == "answer"
    assert detail.status is attempt.status
    assert detail.result is None
    assert results.read_count == 0


def test_reviewed_detail_contains_complete_result():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit().review()
    result = AssessmentResult.create(attempt.id, 8, 10, "Good work")
    service, _, attempt, _ = detail_service(attempt, result)

    detail = service.get_owned(attempt.id, attempt.student_id).detail

    assert detail.result is not None
    assert detail.result.id == result.id
    assert detail.result.attempt_id == attempt.id
    assert detail.result.score == 8
    assert detail.result.max_score == 10
    assert detail.result.feedback == "Good work"


def test_detail_enforces_ownership():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer")
    service, _, attempt, _ = detail_service(attempt)

    with pytest.raises(AssessmentAttemptNotFoundError):
        service.get_owned(attempt.id, uuid4())


def test_detail_requires_valid_definition_scope_binding():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer")
    service, _, attempt, _ = detail_service(attempt, include_definition=False)

    with pytest.raises(AssessmentAttemptNotFoundError):
        service.get_owned(attempt.id, attempt.student_id)


def test_reviewed_detail_requires_its_result():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit().review()
    service, _, attempt, _ = detail_service(attempt)

    with pytest.raises(AssessmentAttemptResultMissingError):
        service.get_owned(attempt.id, attempt.student_id)
