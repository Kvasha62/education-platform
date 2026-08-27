from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptDetail,
    AssessmentAttemptDetailService,
    AssessmentAttemptNotFoundError,
    AssessmentAttemptPage,
    AssessmentAttemptService,
)
from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.attempts import AssessmentAttempt, AssessmentAttemptStatus
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_scope import (
    ActivityScopeResolution,
    ActivityTeacherSpaceScopeQuery,
)
from app.teacher_space.application.assessment_results import (
    TeacherAssessmentReviewAuthorizationError,
    TeacherAssessmentReviewNotFoundError,
    TeacherAssessmentReviewService,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import TeacherSpace


class TeacherSpaces:
    def __init__(self, space):
        self.space = space

    def get_by_id(self, teacher_space_id):
        if self.space.id != teacher_space_id:
            raise TeacherSpaceNotFoundError
        return self.space

    def get_owned(self, teacher_space_id, owner_user_id):
        if (
            self.space.id != teacher_space_id
            or self.space.owner_user_id != owner_user_id
        ):
            raise TeacherSpaceNotFoundError
        return self.space


class Scope:
    def __init__(self, resolution):
        self.resolution = resolution

    def belongs_to_teacher_space(self, activity_id, teacher_space_id):
        return self.resolution is ActivityScopeResolution.IN_SCOPE

    def resolve_activity_scope(self, activity_id, teacher_space_id):
        return self.resolution


class AttemptState:
    def __init__(self, attempt):
        self.attempt = attempt

    def get(self, attempt_id, definition_id):
        if (
            self.attempt is not None
            and self.attempt.id == attempt_id
            and self.attempt.assessment_definition_id == definition_id
        ):
            return self.attempt
        return None


class Attempts:
    def __init__(self, definition, state):
        self.definition = definition
        self.state = state

    def get_definition_by_activity(self, activity_id):
        return self.definition if self.definition.activity_id == activity_id else None

    def get_for_definition(self, attempt_id, definition_id):
        attempt = self.state.get(attempt_id, definition_id)
        if attempt is None:
            raise AssessmentAttemptNotFoundError
        return attempt

    def list_for_definition(self, definition_id, *, status, offset, limit):
        attempt = self.state.attempt
        if attempt is None or attempt.assessment_definition_id != definition_id:
            return []
        if status is not None and attempt.status is not status:
            return []
        return [attempt]


class Details:
    def __init__(self, attempt_id, definition, state):
        self.attempt_id = attempt_id
        self.definition = definition
        self.state = state

    def _detail(self, definition_id):
        attempt = self.state.attempt
        assert attempt is not None
        result = None
        if attempt.status is AssessmentAttemptStatus.REVIEWED:
            result = self.state.result
        return AssessmentAttemptDetail(
            id=attempt.id,
            student_id=attempt.student_id,
            assessment_definition_id=definition_id,
            submission=attempt.submission,
            status=attempt.status,
            result=result,
        )

    def get_for_definition(self, attempt_id, definition_id):
        attempt = self.state.get(attempt_id, definition_id)
        if attempt is None:
            raise AssessmentAttemptNotFoundError
        return self._detail(definition_id)

    def list_for_definition(self, definition_id, *, status, page, page_size):
        attempt = self.state.attempt
        if attempt is None or attempt.assessment_definition_id != definition_id:
            return AssessmentAttemptPage(items=[], has_next=False)
        if status is not None and attempt.status is not status:
            return AssessmentAttemptPage(items=[], has_next=False)
        return AssessmentAttemptPage(items=[self._detail(definition_id)], has_next=False)


class Results:
    def __init__(self, state):
        self.state = state
        self.add_count = 0
        self.update_count = 0

    def get_by_attempt(self, attempt_id):
        result = self.state.result
        return result if result and result.attempt_id == attempt_id else None

    def get(self, result_id, attempt_id):
        result = self.state.result
        return result if result and result.id == result_id else None

    def review(self, attempt_id, definition_id, activity_id, score, max_score, feedback):
        attempt = self.state.get(attempt_id, definition_id)
        if attempt is None:
            from app.assessment.application.attempts import AssessmentAttemptNotFoundError

            raise AssessmentAttemptNotFoundError
        self.state.attempt = attempt.review()
        self.state.result = AssessmentResult.create(attempt_id, score, max_score, feedback)
        self.add_count += 1
        return self.state.result

    def correct(
        self,
        result_id,
        attempt_id,
        definition_id,
        activity_id,
        score,
        feedback,
    ):
        result = self.get(result_id, attempt_id)
        if result is None:
            from app.assessment.application.results import AssessmentResultNotFoundError

            raise AssessmentResultNotFoundError
        self.state.result = result.correct(score, feedback)
        self.update_count += 1
        return self.state.result


class ModelState:
    attempt: AssessmentAttempt
    result: AssessmentResult | None = None

    def get(self, attempt_id, definition_id):
        if (
            self.attempt is not None
            and self.attempt.id == attempt_id
            and self.attempt.assessment_definition_id == definition_id
        ):
            return self.attempt
        return None


def build_service(owner, resolution=ActivityScopeResolution.IN_SCOPE):
    activity_id = uuid4()
    space = TeacherSpace.create(owner, "Space")
    definition = AssessmentDefinition.create(activity_id, None)
    attempt = AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
    state = ModelState()
    state.attempt = attempt
    attempts = Attempts(definition, state)
    details = Details(attempt.id, definition, state)
    results = Results(state)
    service = TeacherAssessmentReviewService(
        cast(TeacherSpaceService, TeacherSpaces(space)),
        ActivityTeacherSpaceScopeQuery(Scope(resolution)),
        cast(AssessmentAttemptService, attempts),
        cast(AssessmentAttemptDetailService, details),
        cast(AssessmentResultService, results),
    )
    return service, space, state, activity_id


def test_authorized_teacher_reviews_and_corrects_result():
    owner = uuid4()
    service, space, state, activity_id = build_service(owner)

    reviewed = service.review(
        owner,
        space.id,
        activity_id,
        state.attempt.id,
        4,
        10,
        "Initial",
    )
    corrected = service.correct(
        owner,
        space.id,
        activity_id,
        state.attempt.id,
        reviewed.id,
        8,
        None,
    )

    assert corrected.id == reviewed.id
    assert corrected.attempt_id == reviewed.attempt_id == state.attempt.id
    assert corrected.max_score == reviewed.max_score == 10
    assert corrected.score == 8
    assert corrected.feedback is None
    assert state.attempt.status is AssessmentAttemptStatus.REVIEWED
    assert state.result == corrected


@pytest.mark.parametrize(
    "resolution", [ActivityScopeResolution.OUTSIDE_SCOPE]
)
def test_out_of_scope_activity_is_authorization_error(resolution):
    owner = uuid4()
    service, space, state, activity_id = build_service(owner, resolution)

    with pytest.raises(TeacherAssessmentReviewAuthorizationError):
        service.review(owner, space.id, activity_id, state.attempt.id, 4, 10)


def test_unknown_teacher_space_is_not_found():
    owner = uuid4()
    service, _, state, activity_id = build_service(owner)

    with pytest.raises(TeacherAssessmentReviewNotFoundError):
        service.get_attempt(owner, uuid4(), activity_id, state.attempt.id)


def test_review_requires_teacher_authorization():
    owner = uuid4()
    service, space, state, activity_id = build_service(owner)

    with pytest.raises(TeacherAssessmentReviewAuthorizationError):
        service.review(
            uuid4(),
            space.id,
            activity_id,
            state.attempt.id,
            4,
            10,
        )


def test_correct_requires_teacher_authorization():
    owner = uuid4()
    service, space, state, activity_id = build_service(owner)
    reviewed = service.review(owner, space.id, activity_id, state.attempt.id, 4, 10)

    with pytest.raises(TeacherAssessmentReviewAuthorizationError):
        service.correct(
            uuid4(),
            space.id,
            activity_id,
            state.attempt.id,
            reviewed.id,
            8,
            None,
        )
