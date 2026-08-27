from uuid import uuid4

import pytest

from app.assessment.application.attempts import AssessmentAttemptNotFoundError
from app.assessment.application.results import (
    AssessmentResultNotFoundError,
    AssessmentResultService,
)
from app.assessment.domain.attempts import (
    AssessmentAttempt,
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
)
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

    def get_by_id(self, definition_id):
        return self.definition if self.definition.id == definition_id else None

    def get_by_activity(self, activity_id):
        return self.definition if self.definition.activity_id == activity_id else None

    def add(self, definition):
        return definition

    def update(self, definition):
        return definition


class Attempts:
    def __init__(self, attempt):
        self.items = {attempt.id: attempt}

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
        attempt = self.get(attempt_id, definition_id)
        return attempt if attempt and attempt.student_id == student_id else None

    def get_owned_by_id(self, attempt_id, student_id):
        attempt = self.items.get(attempt_id)
        return attempt if attempt and attempt.student_id == student_id else None

    def update(self, attempt):
        self.items[attempt.id] = attempt
        return attempt

    def list_owned(self, definition_id, student_id):
        return []


class Results:
    def __init__(self, fail_creation=False):
        self.items = {}
        self.fail_creation = fail_creation
        self.add_count = 0
        self.update_count = 0

    def add(self, result):
        self.add_count += 1
        if self.fail_creation:
            raise RuntimeError("result creation failed")
        self.items[result.id] = result
        return result

    def get(self, result_id, attempt_id):
        result = self.items.get(result_id)
        return result if result and result.attempt_id == attempt_id else None

    def get_by_attempt(self, attempt_id):
        return next(
            (result for result in self.items.values() if result.attempt_id == attempt_id),
            None,
        )

    def update(self, result):
        self.items[result.id] = result
        self.update_count += 1
        return result


def result_service():
    activity_id = uuid4()
    definition = AssessmentDefinition.create(activity_id, None)
    attempt = AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
    attempts = Attempts(attempt)
    results = Results()
    service = AssessmentResultService(results, attempts, Definitions(definition))
    return service, attempts, results, activity_id, definition, attempt


def test_submitted_attempt_review_creates_scored_result():
    service, attempts, results, activity_id, definition, attempt = result_service()

    result = service.review(
        attempt.id,
        definition.id,
        activity_id,
        7,
        10,
        "Good work",
    )

    assert attempts.items[attempt.id].status is AssessmentAttemptStatus.REVIEWED
    assert result.attempt_id == attempt.id
    assert result.score == 7
    assert result.max_score == 10
    assert result.feedback == "Good work"
    assert list(results.items.values()) == [result]
    assert results.add_count == 1


def test_review_normalizes_blank_feedback():
    service, _, _, activity_id, definition, attempt = result_service()

    result = service.review(attempt.id, definition.id, activity_id, 7, 10, "   ")

    assert result.feedback is None


def test_result_creation_failure_does_not_review_attempt():
    service, attempts, _, activity_id, definition, attempt = result_service()
    failing_results = Results(fail_creation=True)
    service.results = failing_results

    with pytest.raises(RuntimeError, match="result creation failed"):
        service.review(attempt.id, definition.id, activity_id, 7, 10)

    assert attempts.items[attempt.id].status is AssessmentAttemptStatus.SUBMITTED
    assert not failing_results.items


def test_reviewed_attempt_cannot_be_reviewed_again():
    service, attempts, results, activity_id, definition, attempt = result_service()
    first = service.review(attempt.id, definition.id, activity_id, 7, 10)

    with pytest.raises(AssessmentAttemptImmutableError):
        service.review(attempt.id, definition.id, activity_id, 8, 10)

    reviewed = attempts.items[attempt.id]
    assert reviewed.status is AssessmentAttemptStatus.REVIEWED
    assert list(results.items.values()) == [first]
    assert results.add_count == 1


def test_correction_updates_existing_result_and_keeps_reviewed_attempt():
    service, attempts, results, activity_id, definition, attempt = result_service()
    result = service.review(attempt.id, definition.id, activity_id, 4, 10, "Initial")

    corrected = service.correct(
        result.id,
        attempt.id,
        definition.id,
        activity_id,
        8,
        "Corrected",
    )

    assert corrected.id == result.id
    assert corrected.attempt_id == result.attempt_id
    assert corrected.max_score == result.max_score
    assert corrected.score == 8
    assert corrected.feedback == "Corrected"
    assert attempts.items[attempt.id].status is AssessmentAttemptStatus.REVIEWED
    assert len(attempts.items) == 1
    assert list(results.items.values()) == [corrected]
    assert results.add_count == 1
    assert results.update_count == 1


def test_correction_can_clear_feedback():
    service, _, results, activity_id, definition, attempt = result_service()
    result = service.review(attempt.id, definition.id, activity_id, 4, 10, "Initial")

    corrected = service.correct(
        result.id,
        attempt.id,
        definition.id,
        activity_id,
        5,
        "\t ",
    )

    assert corrected.feedback is None
    assert list(results.items.values()) == [corrected]


def test_correction_requires_reviewed_attempt():
    service, _, _, activity_id, definition, attempt = result_service()

    with pytest.raises(AssessmentResultNotFoundError):
        service.correct(
            uuid4(),
            attempt.id,
            definition.id,
            activity_id,
            5,
            None,
        )


def test_correction_requires_existing_result():
    service, attempts, results, activity_id, definition, attempt = result_service()
    original = service.review(attempt.id, definition.id, activity_id, 4, 10)

    with pytest.raises(AssessmentResultNotFoundError):
        service.correct(
            uuid4(),
            attempt.id,
            definition.id,
            activity_id,
            5,
            None,
        )

    assert attempts.items[attempt.id].status is AssessmentAttemptStatus.REVIEWED
    assert list(results.items.values()) == [original]
    assert results.update_count == 0


def test_result_operations_are_bound_to_definition_activity_scope():
    service, attempts, results, activity_id, definition, attempt = result_service()

    with pytest.raises(AssessmentAttemptNotFoundError):
        service.review(attempt.id, definition.id, uuid4(), 7, 10)
    assert attempts.items[attempt.id].status is AssessmentAttemptStatus.SUBMITTED
    assert not results.items

    result = service.review(attempt.id, definition.id, activity_id, 7, 10)
    with pytest.raises(AssessmentAttemptNotFoundError):
        service.correct(
            result.id,
            attempt.id,
            definition.id,
            uuid4(),
            8,
            None,
        )
