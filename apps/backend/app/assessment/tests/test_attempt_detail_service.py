from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptDetailService,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptResultMissingError,
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
            if self.definition.id == definition_id
            and self.definition.activity_id == activity_id
            else None
        )


class Attempts:
    def __init__(self, attempt):
        self.attempt = attempt

    def get_owned(self, attempt_id, definition_id, student_id):
        return (
            self.attempt
            if self.attempt.id == attempt_id
            and self.attempt.assessment_definition_id == definition_id
            and self.attempt.student_id == student_id
            else None
        )


class Results:
    def __init__(self, result=None):
        self.result = result
        self.read_count = 0

    def get_by_attempt(self, attempt_id):
        self.read_count += 1
        return self.result if self.result and self.result.attempt_id == attempt_id else None


def detail_service(attempt, result=None):
    definition = AssessmentDefinition.create(uuid4(), None)
    attempt = AssessmentAttempt(
        attempt.id,
        definition.id,
        attempt.student_id,
        attempt.submission,
        attempt.status,
    )
    results = Results(result)
    if result is not None:
        results.result = AssessmentResult(
            result.id,
            attempt.id,
            result.score,
            result.max_score,
            result.feedback,
        )
    service = AssessmentAttemptDetailService(
        cast(AssessmentAttemptRepository, Attempts(attempt)),
        cast(AssessmentDefinitionRepository, Definitions(definition)),
        cast(AssessmentResultRepository, results),
    )
    return service, definition, attempt, results


@pytest.mark.parametrize("submitted", [False, True])
def test_draft_and_submitted_detail_have_no_result(submitted):
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer")
    if submitted:
        attempt = attempt.submit()
    service, definition, attempt, results = detail_service(attempt)

    detail = service.get_owned(
        attempt.id,
        definition.id,
        definition.activity_id,
        attempt.student_id,
    )

    assert detail.id == attempt.id
    assert detail.assessment_definition_id == definition.id
    assert detail.submission == "answer"
    assert detail.status is attempt.status
    assert detail.result is None
    assert results.read_count == 0


def test_reviewed_detail_contains_complete_result():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit().review()
    result = AssessmentResult.create(attempt.id, 8, 10, "Good work")
    service, definition, attempt, _ = detail_service(attempt, result)

    detail = service.get_owned(
        attempt.id,
        definition.id,
        definition.activity_id,
        attempt.student_id,
    )

    assert detail.result is not None
    assert detail.result.id == result.id
    assert detail.result.attempt_id == attempt.id
    assert detail.result.score == 8
    assert detail.result.max_score == 10
    assert detail.result.feedback == "Good work"


def test_detail_enforces_ownership_and_assessment_scope():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer")
    service, definition, attempt, _ = detail_service(attempt)

    for operation in (
        lambda: service.get_owned(
            attempt.id,
            definition.id,
            uuid4(),
            attempt.student_id,
        ),
        lambda: service.get_owned(
            attempt.id,
            definition.id,
            definition.activity_id,
            uuid4(),
        ),
    ):
        with pytest.raises(AssessmentAttemptNotFoundError):
            operation()


def test_reviewed_detail_requires_its_result():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit().review()
    service, definition, attempt, _ = detail_service(attempt)

    with pytest.raises(AssessmentAttemptResultMissingError):
        service.get_owned(
            attempt.id,
            definition.id,
            definition.activity_id,
            attempt.student_id,
        )
