from uuid import uuid4

import pytest

from app.assessment.domain.attempts import (
    AssessmentAttempt,
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
)


def test_draft_edit_submit_and_immutability():
    a = AssessmentAttempt.create(uuid4(), uuid4(), None)
    assert a.status is AssessmentAttemptStatus.DRAFT
    a = a.update_submission("")
    a = a.submit()
    assert a.status is AssessmentAttemptStatus.SUBMITTED
    with pytest.raises(AssessmentAttemptImmutableError):
        a.update_submission("x")
    with pytest.raises(AssessmentAttemptImmutableError):
        a.submit()


def test_resubmission_is_new_attempt():
    d, s = uuid4(), uuid4()
    old = AssessmentAttempt.create(d, s, "one").submit()
    new = AssessmentAttempt.create(d, s, "two")
    assert (
        old.id != new.id
        and old.status is AssessmentAttemptStatus.SUBMITTED
        and new.status is AssessmentAttemptStatus.DRAFT
    )
