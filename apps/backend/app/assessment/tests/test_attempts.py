from uuid import uuid4

import pytest

from app.assessment.domain.attempts import (
    AssessmentAttempt,
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
    AssessmentSubmissionRequiredError,
    InvalidAssessmentSubmissionError,
)


@pytest.mark.parametrize("submission", [None, "", "   ", "\t\n"])
def test_draft_creation_normalizes_empty_submission_to_none(submission):
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), submission)

    assert attempt.status is AssessmentAttemptStatus.DRAFT
    assert attempt.submission is None


def test_submission_must_be_plain_text_or_none():
    with pytest.raises(InvalidAssessmentSubmissionError):
        AssessmentAttempt.create(uuid4(), uuid4(), 1)  # type: ignore[arg-type]


def test_draft_can_be_created_with_submission_and_fully_replaced_or_cleared():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "first")

    replaced = attempt.update_submission("second")
    cleared = replaced.update_submission("  ")
    restored = cleared.update_submission("third")

    assert attempt.submission == "first"
    assert replaced.submission == "second"
    assert cleared.submission is None
    assert restored.submission == "third"


@pytest.mark.parametrize("submission", [None, "", "   ", "\t\n"])
def test_empty_draft_cannot_be_submitted(submission):
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), submission)

    with pytest.raises(AssessmentSubmissionRequiredError):
        attempt.submit()

    assert attempt.status is AssessmentAttemptStatus.DRAFT
    assert attempt.submission is None


def test_meaningful_draft_submits_and_becomes_immutable():
    attempt = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit()

    assert attempt.status is AssessmentAttemptStatus.SUBMITTED
    assert attempt.submission == "answer"
    with pytest.raises(AssessmentAttemptImmutableError):
        attempt.update_submission("changed")
    with pytest.raises(AssessmentAttemptImmutableError):
        attempt.submit()


def test_submitted_attempt_can_be_reviewed_once_and_remains_immutable():
    reviewed = AssessmentAttempt.create(uuid4(), uuid4(), "answer").submit().review()

    assert reviewed.status is AssessmentAttemptStatus.REVIEWED
    assert reviewed.submission == "answer"
    for operation in (
        lambda: reviewed.update_submission("changed"),
        reviewed.submit,
        reviewed.review,
    ):
        with pytest.raises(AssessmentAttemptImmutableError):
            operation()


def test_draft_attempt_cannot_be_reviewed():
    with pytest.raises(AssessmentAttemptImmutableError):
        AssessmentAttempt.create(uuid4(), uuid4(), "answer").review()


def test_resubmission_is_new_attempt():
    definition_id, student_id = uuid4(), uuid4()
    old = AssessmentAttempt.create(definition_id, student_id, "one").submit()
    new = AssessmentAttempt.create(definition_id, student_id, "two")

    assert old.id != new.id
    assert old.status is AssessmentAttemptStatus.SUBMITTED
    assert new.status is AssessmentAttemptStatus.DRAFT
