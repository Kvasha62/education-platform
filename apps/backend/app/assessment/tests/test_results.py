from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.assessment.domain.results import (
    AssessmentResult,
    InvalidAssessmentResultMaxScoreError,
    InvalidAssessmentResultScoreError,
)


def test_result_contains_approved_fields():
    attempt_id = uuid4()
    result = AssessmentResult.create(attempt_id, 7, 10, "Good work")

    assert result.attempt_id == attempt_id
    assert result.score == 7
    assert result.max_score == 10
    assert result.feedback == "Good work"


@pytest.mark.parametrize("max_score", [0, -1, True, 1.5])
def test_max_score_must_be_a_positive_integer(max_score):
    with pytest.raises(InvalidAssessmentResultMaxScoreError):
        AssessmentResult.create(uuid4(), 0, max_score)


@pytest.mark.parametrize("score", [-1, 11, True, 1.5])
def test_score_must_be_an_integer_in_result_range(score):
    with pytest.raises(InvalidAssessmentResultScoreError):
        AssessmentResult.create(uuid4(), score, 10)


@pytest.mark.parametrize("score", [0, 10])
def test_score_range_boundaries_are_inclusive(score):
    assert AssessmentResult.create(uuid4(), score, 10).score == score


@pytest.mark.parametrize("feedback", [None, "", "   ", "\t\n"])
def test_blank_feedback_is_normalized_to_none(feedback):
    assert AssessmentResult.create(uuid4(), 1, 10, feedback).feedback is None


def test_non_blank_feedback_has_no_milestone_length_limit():
    feedback = "x" * 100_000

    assert AssessmentResult.create(uuid4(), 1, 10, feedback).feedback == feedback


def test_correction_changes_score_and_feedback_but_preserves_identity_and_max_score():
    result = AssessmentResult.create(uuid4(), 4, 10, "Initial")

    corrected = result.correct(8, "Corrected")

    assert corrected.id == result.id
    assert corrected.attempt_id == result.attempt_id
    assert corrected.max_score == result.max_score
    assert corrected.score == 8
    assert corrected.feedback == "Corrected"
    with pytest.raises(FrozenInstanceError):
        corrected.max_score = 20  # type: ignore[misc]


def test_correction_can_clear_feedback():
    result = AssessmentResult.create(uuid4(), 4, 10, "Initial")

    corrected = result.correct(5, "   ")

    assert corrected.score == 5
    assert corrected.feedback is None


def test_correction_enforces_original_max_score():
    result = AssessmentResult.create(uuid4(), 4, 10)

    with pytest.raises(InvalidAssessmentResultScoreError):
        result.correct(11, None)
