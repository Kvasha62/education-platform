from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptDefinitionNotFoundError,
    AssessmentAttemptDetailService,
    AssessmentAttemptService,
)
from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.attempts import (
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
)
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_publication import PublishedActivityReference
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.domain.models import EnrollmentStatus
from app.student_space.application.assessment_attempts import (
    AssessmentAttemptAuthorizationError,
    AssessmentAttemptMutationForbiddenError,
    StudentAssessmentAttemptService,
)


class Activities:
    def __init__(self, visible=True):
        self.visible = visible
        self.course_id = uuid4()
        self.read_count = 0

    def require_published(self, activity_id):
        self.read_count += 1
        if not self.visible:
            raise PublishedActivityNotFoundError
        return PublishedActivityReference(activity_id, self.course_id, "Activity")


class Enrollments:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def get_status(self, student_id, course_id):
        return EnrollmentStatus.ENROLLED if self.allowed else None


class Definitions:
    def __init__(self, definitions):
        self.definitions = definitions

    def get(self, definition_id, activity_id):
        return next(
            (
                definition
                for definition in self.definitions
                if definition.id == definition_id
                and definition.activity_id == activity_id
            ),
            None,
        )

    def get_by_id(self, definition_id):
        return next(
            (
                definition
                for definition in self.definitions
                if definition.id == definition_id
            ),
            None,
        )

    def get_by_activity(self, activity_id):
        return next(
            (
                definition
                for definition in self.definitions
                if definition.activity_id == activity_id
            ),
            None,
        )

    def add(self, value):
        return value

    def update(self, value):
        return value


class Attempts:
    def __init__(self):
        self.items = {}

    def add(self, value):
        self.items[value.id] = value
        return value

    def get(self, attempt_id, definition_id):
        value = self.items.get(attempt_id)
        return (
            value if value and value.assessment_definition_id == definition_id else None
        )

    def get_owned(self, attempt_id, definition_id, student_id):
        value = self.get(attempt_id, definition_id)
        return value if value and value.student_id == student_id else None

    def get_owned_by_id(self, attempt_id, student_id):
        value = self.items.get(attempt_id)
        return value if value and value.student_id == student_id else None

    def update(self, value):
        self.items[value.id] = value
        return value

    def list_owned(self, definition_id, student_id):
        return []


class Results:
    def __init__(self):
        self.items = {}

    def add(self, value):
        self.items[value.id] = value
        return value

    def get(self, result_id, attempt_id):
        value = self.items.get(result_id)
        return value if value and value.attempt_id == attempt_id else None

    def get_by_attempt(self, attempt_id):
        return next(
            (value for value in self.items.values() if value.attempt_id == attempt_id),
            None,
        )

    def update(self, value):
        self.items[value.id] = value
        return value


def service_for(definition, *, visible=True, enrolled=True):
    definitions = Definitions([definition])
    attempts = Attempts()
    results = Results()
    attempt_service = AssessmentAttemptService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
    )
    detail_service = AssessmentAttemptDetailService(
        attempt_service,
        cast(AssessmentResultRepository, results),
    )
    activities = Activities(visible)
    service = StudentAssessmentAttemptService(
        activities,
        Enrollments(enrolled),
        attempt_service,
        detail_service,
    )
    return service, activities, attempts, results, definitions


def test_create_requires_published_activity_and_enrollment():
    definition = AssessmentDefinition.create(uuid4(), None)

    hidden, _, _, _, _ = service_for(definition, visible=False)
    with pytest.raises(AssessmentAttemptAuthorizationError):
        hidden.create(uuid4(), definition.activity_id, definition.id, None)

    unenrolled, _, _, _, _ = service_for(definition, enrolled=False)
    with pytest.raises(AssessmentAttemptMutationForbiddenError):
        unenrolled.create(uuid4(), definition.activity_id, definition.id, None)


def test_invalid_definition_scope_precedes_enrollment_denial():
    definition = AssessmentDefinition.create(uuid4(), None)
    service, activities, attempts, _, _ = service_for(definition, enrolled=False)

    with pytest.raises(AssessmentAttemptDefinitionNotFoundError):
        service.create(uuid4(), uuid4(), definition.id, None)

    assert activities.read_count == 0
    assert not attempts.items


def test_create_is_non_idempotent_and_returns_complete_draft_detail():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, _, attempts, _, _ = service_for(definition)

    first = service.create(student_id, definition.activity_id, definition.id, "  ")
    second = service.create(student_id, definition.activity_id, definition.id, "answer")

    assert first.id != second.id
    assert first.status is AssessmentAttemptStatus.DRAFT
    assert first.submission is None
    assert first.result is None
    assert second.submission == "answer"
    assert len(attempts.items) == 2


def test_replace_is_repeat_safe_and_can_clear_submission():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, _, _, _, _ = service_for(definition)
    attempt = service.create(student_id, definition.activity_id, definition.id, None)

    replaced = service.update_submission(student_id, attempt.id, "answer")
    repeated = service.update_submission(student_id, attempt.id, "answer")
    cleared = service.update_submission(student_id, attempt.id, "   ")

    assert replaced.submission == "answer"
    assert repeated.submission == "answer"
    assert repeated.id == replaced.id
    assert cleared.submission is None


def test_owned_draft_mutation_and_read_require_current_access():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, activities, attempts, results, definitions = service_for(definition)
    detail = service.create(student_id, definition.activity_id, definition.id, "answer")
    activities.visible = False

    for operation in (
        lambda: service.update_submission(student_id, detail.id, "changed"),
        lambda: service.submit(student_id, detail.id),
        lambda: service.get(student_id, detail.id),
    ):
        with pytest.raises(AssessmentAttemptMutationForbiddenError):
            operation()

    assert attempts.items[detail.id].status is AssessmentAttemptStatus.DRAFT
    assert not results.items
    assert definitions.get_by_id(definition.id) == definition


def test_wrong_owner_and_invalid_definition_binding_are_concealed():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, _, attempts, _, definitions = service_for(definition)
    detail = service.create(student_id, definition.activity_id, definition.id, "answer")

    with pytest.raises(AssessmentAttemptAuthorizationError):
        service.get(uuid4(), detail.id)

    definitions.definitions.clear()
    with pytest.raises(AssessmentAttemptAuthorizationError):
        service.get(student_id, detail.id)
    assert detail.id in attempts.items


def test_submitted_and_reviewed_mutations_are_conflicts_before_current_access():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, activities, attempts, _, _ = service_for(definition)
    draft = service.create(student_id, definition.activity_id, definition.id, "answer")
    submitted = service.submit(student_id, draft.id)
    activities.visible = False
    read_count = activities.read_count

    for operation in (
        lambda: service.update_submission(student_id, submitted.id, "changed"),
        lambda: service.submit(student_id, submitted.id),
    ):
        with pytest.raises(AssessmentAttemptImmutableError):
            operation()
    assert activities.read_count == read_count

    attempts.items[submitted.id] = attempts.items[submitted.id].review()
    with pytest.raises(AssessmentAttemptImmutableError):
        service.submit(student_id, submitted.id)


def test_historical_submitted_and_reviewed_reads_ignore_current_access():
    definition = AssessmentDefinition.create(uuid4(), None)
    student_id = uuid4()
    service, activities, attempts, results, _ = service_for(definition)
    draft = service.create(student_id, definition.activity_id, definition.id, "answer")
    submitted = service.submit(student_id, draft.id)
    activities.visible = False
    read_count = activities.read_count

    submitted_detail = service.get(student_id, submitted.id)
    assert submitted_detail.status is AssessmentAttemptStatus.SUBMITTED
    assert submitted_detail.result is None

    reviewed = attempts.items[submitted.id].review()
    attempts.items[submitted.id] = reviewed
    result = results.add(AssessmentResult.create(reviewed.id, 8, 10, "Good work"))
    reviewed_detail = service.get(student_id, reviewed.id)

    assert activities.read_count == read_count
    assert reviewed_detail.status is AssessmentAttemptStatus.REVIEWED
    assert reviewed_detail.result == result
