from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.assessment.domain.results import AssessmentResult


def test_result_belongs_to_one_attempt():
    attempt_id = uuid4()
    result = AssessmentResult.create(attempt_id)

    assert result.attempt_id == attempt_id
    with pytest.raises(FrozenInstanceError):
        result.attempt_id = uuid4()  # type: ignore[misc]
