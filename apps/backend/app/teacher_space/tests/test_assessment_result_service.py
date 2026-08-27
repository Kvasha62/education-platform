from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_scope import ActivityTeacherSpaceScopeQuery
from app.teacher_space.application.assessment_results import (
    AssessmentResultAuthorizationError,
    TeacherAssessmentResultService,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace


class TeacherSpaces:
    def __init__(self, space):
        self.space = space

    def get_owned(self, teacher_space_id, owner_user_id):
        if (
            self.space.id != teacher_space_id
            or self.space.owner_user_id != owner_user_id
        ):
            raise TeacherSpaceNotFoundError
        return self.space


class Scope:
    def __init__(self, allowed):
        self.allowed = allowed

    def belongs_to_teacher_space(self, activity_id, teacher_space_id):
        return self.allowed


class Results:
    def __init__(self, attempt_id):
        self.result = AssessmentResult.create(attempt_id)
        self.correct_count = 0

    def review(self, attempt_id, definition_id, activity_id):
        assert attempt_id == self.result.attempt_id
        return self.result

    def correct(self, result_id, attempt_id, definition_id, activity_id):
        assert result_id == self.result.id and attempt_id == self.result.attempt_id
        self.correct_count += 1
        return self.result


def orchestrator(owner, attempt_id, activity_allowed=True):
    space = TeacherSpace.create(owner, "Space")
    results = Results(attempt_id)
    service = TeacherAssessmentResultService(
        cast(TeacherSpaceService, TeacherSpaces(space)),
        ActivityTeacherSpaceScopeQuery(Scope(activity_allowed)),
        cast(AssessmentResultService, results),
    )
    return service, space, results


def test_authorized_teacher_reviews_and_corrects_same_result():
    owner = uuid4()
    activity_id, definition_id, attempt_id = uuid4(), uuid4(), uuid4()
    service, space, results = orchestrator(owner, attempt_id)

    reviewed = service.review(
        owner, space.id, activity_id, definition_id, attempt_id
    )
    corrected = service.correct(
        owner,
        space.id,
        activity_id,
        definition_id,
        attempt_id,
        reviewed.id,
    )

    assert corrected == reviewed
    assert results.correct_count == 1


@pytest.mark.parametrize("wrong_teacher,activity_allowed", [(True, True), (False, False)])
def test_every_result_operation_requires_teacher_and_activity_authorization(
    wrong_teacher, activity_allowed
):
    owner = uuid4()
    activity_id, definition_id, attempt_id = uuid4(), uuid4(), uuid4()
    service, space, results = orchestrator(owner, attempt_id, activity_allowed)
    teacher_id = uuid4() if wrong_teacher else owner

    operations = (
        lambda: service.review(
            teacher_id, space.id, activity_id, definition_id, attempt_id
        ),
        lambda: service.correct(
            teacher_id,
            space.id,
            activity_id,
            definition_id,
            attempt_id,
            results.result.id,
        ),
    )
    for operation in operations:
        with pytest.raises(AssessmentResultAuthorizationError):
            operation()
