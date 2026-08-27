from typing import cast
from uuid import uuid4

import pytest

from app.assessment.application.attempts import (
    AssessmentAttemptDetail,
    AssessmentAttemptDetailService,
    AssessmentAttemptService,
)
from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.attempts import AssessmentAttemptStatus
from app.assessment.domain.results import AssessmentResult
from app.education.application.activity_publication import PublishedActivityReference
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.domain.models import EnrollmentStatus
from app.student_space.application.assessment_attempts import (
    AssessmentAttemptAuthorizationError,
    StudentAssessmentAttemptService,
)


class Activities:
    def __init__(self, visible=True):
        self.visible = visible
        self.course = uuid4()
        self.read_count = 0

    def require_published(self, activity):
        self.read_count += 1
        if not self.visible:
            raise PublishedActivityNotFoundError
        return PublishedActivityReference(activity, self.course, "Activity")


class Enrollments:
    def __init__(self, allowed):
        self.allowed = allowed

    def get_status(self, student_id, course_id):
        return EnrollmentStatus.ENROLLED if self.allowed else None


class Attempts:
    def create(self, definition_id, activity_id, student_id, submission):
        return "created"

    def update_submission(self, *args):
        return "updated"

    def submit(self, *args):
        return "submitted"


class Details:
    def __init__(self, status=AssessmentAttemptStatus.DRAFT):
        attempt_id = uuid4()
        result = (
            AssessmentResult.create(attempt_id, 8, 10, "Good work")
            if status is AssessmentAttemptStatus.REVIEWED
            else None
        )
        self.detail = AssessmentAttemptDetail(
            id=attempt_id,
            assessment_definition_id=uuid4(),
            submission="answer",
            status=status,
            result=result,
        )

    def get_owned(self, *args):
        return self.detail


def student_service(visible=True, enrolled=True, status=AssessmentAttemptStatus.DRAFT):
    activities = Activities(visible)
    service = StudentAssessmentAttemptService(
        activities,
        Enrollments(enrolled),
        cast(AssessmentAttemptService, Attempts()),
        cast(AssessmentAttemptDetailService, Details(status)),
    )
    return service, activities


@pytest.mark.parametrize("visible,enrolled", [(False, True), (True, False)])
def test_every_student_mutation_requires_visibility_and_enrollment(visible, enrolled):
    service, _ = student_service(visible, enrolled)
    student_id, activity_id, definition_id, attempt_id = [uuid4() for _ in range(4)]

    for operation in (
        lambda: service.create(student_id, activity_id, definition_id, None),
        lambda: service.update_submission(
            student_id,
            activity_id,
            definition_id,
            attempt_id,
            "answer",
        ),
        lambda: service.submit(student_id, activity_id, definition_id, attempt_id),
    ):
        with pytest.raises(AssessmentAttemptAuthorizationError):
            operation()


def test_draft_read_requires_visibility_and_enrollment():
    student_id, activity_id, definition_id, attempt_id = [uuid4() for _ in range(4)]
    for visible, enrolled in ((False, True), (True, False)):
        service, _ = student_service(visible, enrolled, AssessmentAttemptStatus.DRAFT)

        with pytest.raises(AssessmentAttemptAuthorizationError):
            service.get(student_id, activity_id, definition_id, attempt_id)


@pytest.mark.parametrize(
    "status",
    [AssessmentAttemptStatus.SUBMITTED, AssessmentAttemptStatus.REVIEWED],
)
def test_historical_read_does_not_require_current_visibility_or_enrollment(status):
    service, activities = student_service(False, False, status)

    detail = service.get(uuid4(), uuid4(), uuid4(), uuid4())

    assert detail.status is status
    assert (detail.result is not None) is (status is AssessmentAttemptStatus.REVIEWED)
    assert activities.read_count == 0


def test_authorized_student_operations_are_delegated():
    service, _ = student_service()
    student_id, activity_id, definition_id, attempt_id = [uuid4() for _ in range(4)]

    assert service.create(student_id, activity_id, definition_id, None) == "created"
    assert (
        service.update_submission(
            student_id,
            activity_id,
            definition_id,
            attempt_id,
            "answer",
        )
        == "updated"
    )
    assert service.submit(student_id, activity_id, definition_id, attempt_id) == "submitted"
    assert service.get(student_id, activity_id, definition_id, attempt_id).status is (
        AssessmentAttemptStatus.DRAFT
    )


class DefinitionRepository:
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


class AttemptRepository:
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
        value = self.items.get(attempt_id)
        return (
            value
            if value
            and value.assessment_definition_id == definition_id
            and value.student_id == student_id
            else None
        )

    def update(self, value):
        self.items[value.id] = value
        return value

    def list_owned(self, definition_id, student_id):
        return []


class ResultRepository:
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


def test_attempt_operations_deny_mismatched_activity_and_student_ownership():
    from app.assessment.domain.models import AssessmentDefinition

    student_id, activity_a, activity_b = uuid4(), uuid4(), uuid4()
    definition_a = AssessmentDefinition.create(activity_a, None)
    definition_b = AssessmentDefinition.create(activity_b, None)
    definitions = DefinitionRepository([definition_a, definition_b])
    attempts = AttemptRepository()
    results = ResultRepository()
    assessment = AssessmentAttemptService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
    )
    details = AssessmentAttemptDetailService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
        cast(AssessmentResultRepository, results),
    )
    attempt_a = assessment.create(definition_a.id, activity_a, student_id, "a")
    attempt_b = assessment.create(definition_b.id, activity_b, student_id, "b")
    student = StudentAssessmentAttemptService(
        Activities(), Enrollments(True), assessment, details
    )

    operations = (
        lambda: student.get(student_id, activity_a, definition_b.id, attempt_b.id),
        lambda: student.update_submission(
            student_id,
            activity_a,
            definition_b.id,
            attempt_b.id,
            "changed",
        ),
        lambda: student.submit(
            student_id,
            activity_a,
            definition_b.id,
            attempt_b.id,
        ),
        lambda: student.get(uuid4(), activity_a, definition_a.id, attempt_a.id),
    )
    for operation in operations:
        with pytest.raises(AssessmentAttemptAuthorizationError):
            operation()

    assert student.get(student_id, activity_a, definition_a.id, attempt_a.id).id == (
        attempt_a.id
    )


def test_historical_owned_attempt_remains_readable_without_current_access():
    from app.assessment.domain.models import AssessmentDefinition

    student_id, activity_id = uuid4(), uuid4()
    definition = AssessmentDefinition.create(activity_id, None)
    definitions = DefinitionRepository([definition])
    attempts = AttemptRepository()
    results = ResultRepository()
    assessment = AssessmentAttemptService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
    )
    details = AssessmentAttemptDetailService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
        cast(AssessmentResultRepository, results),
    )
    attempt = assessment.create(definition.id, activity_id, student_id, "answer")
    attempt = assessment.submit(attempt.id, definition.id, activity_id, student_id)
    student = StudentAssessmentAttemptService(
        Activities(False), Enrollments(False), assessment, details
    )

    detail = student.get(student_id, activity_id, definition.id, attempt.id)

    assert detail.id == attempt.id
    assert detail.status is AssessmentAttemptStatus.SUBMITTED
    assert detail.result is None


def test_reviewed_aggregate_with_result_remains_readable_without_current_access():
    from app.assessment.domain.models import AssessmentDefinition

    student_id, activity_id = uuid4(), uuid4()
    definition = AssessmentDefinition.create(activity_id, None)
    definitions = DefinitionRepository([definition])
    attempts = AttemptRepository()
    results = ResultRepository()
    assessment = AssessmentAttemptService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
    )
    details = AssessmentAttemptDetailService(
        cast(AssessmentAttemptRepository, attempts),
        cast(AssessmentDefinitionRepository, definitions),
        cast(AssessmentResultRepository, results),
    )
    attempt = assessment.create(definition.id, activity_id, student_id, "answer")
    attempt = assessment.submit(attempt.id, definition.id, activity_id, student_id)
    reviewed = attempts.update(attempt.review())
    result = results.add(AssessmentResult.create(reviewed.id, 8, 10, "Good work"))
    student = StudentAssessmentAttemptService(
        Activities(False), Enrollments(False), assessment, details
    )

    detail = student.get(student_id, activity_id, definition.id, reviewed.id)

    assert detail.status is AssessmentAttemptStatus.REVIEWED
    assert detail.result == result
