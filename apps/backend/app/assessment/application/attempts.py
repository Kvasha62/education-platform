from dataclasses import dataclass
from uuid import UUID

from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.attempts import AssessmentAttempt, AssessmentAttemptStatus
from app.assessment.domain.models import AssessmentDefinitionStatus
from app.assessment.domain.results import AssessmentResult


class AssessmentAttemptNotFoundError(Exception):
    pass


class AssessmentAttemptResultMissingError(Exception):
    pass


class AssessmentDefinitionUnavailableError(Exception):
    pass


class AssessmentAttemptDefinitionNotFoundError(AssessmentDefinitionUnavailableError):
    pass


class AssessmentAttemptDefinitionArchivedError(AssessmentDefinitionUnavailableError):
    pass


class AssessmentAttemptDefinitionInvalidStateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AssessmentAttemptDetail:
    id: UUID
    assessment_definition_id: UUID
    submission: str | None
    status: AssessmentAttemptStatus
    result: AssessmentResult | None


@dataclass(frozen=True, slots=True)
class AssessmentAttemptContext:
    attempt: AssessmentAttempt
    activity_id: UUID


@dataclass(frozen=True, slots=True)
class AssessmentAttemptDetailContext:
    detail: AssessmentAttemptDetail
    activity_id: UUID


class AssessmentAttemptService:
    def __init__(
        self, attempts: AssessmentAttemptRepository, definitions: AssessmentDefinitionRepository
    ):
        self.attempts, self.definitions = attempts, definitions

    def create(
        self,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
        submission: str | None,
    ) -> AssessmentAttempt:
        definition = self.definitions.get(definition_id, activity_id)
        if definition is None:
            raise AssessmentAttemptDefinitionNotFoundError
        if definition.status is AssessmentDefinitionStatus.ACTIVE:
            return self.attempts.add(
                AssessmentAttempt.create(definition_id, student_id, submission)
            )
        if definition.status is AssessmentDefinitionStatus.ARCHIVED:
            raise AssessmentAttemptDefinitionArchivedError
        raise AssessmentAttemptDefinitionInvalidStateError

    def validate_definition_scope(
        self, definition_id: UUID, activity_id: UUID
    ) -> None:
        if self.definitions.get(definition_id, activity_id) is None:
            raise AssessmentAttemptDefinitionNotFoundError

    def update_submission(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
        submission: str | None,
    ) -> AssessmentAttempt:
        return self.attempts.update(
            self._get(attempt_id, definition_id, activity_id, student_id).update_submission(
                submission
            )
        )

    def submit(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
    ) -> AssessmentAttempt:
        return self.attempts.update(
            self._get(attempt_id, definition_id, activity_id, student_id).submit()
        )

    def get(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
    ) -> AssessmentAttempt:
        return self._get(attempt_id, definition_id, activity_id, student_id)

    def resolve_owned(
        self, attempt_id: UUID, student_id: UUID
    ) -> AssessmentAttemptContext:
        attempt = self.attempts.get_owned_by_id(attempt_id, student_id)
        if attempt is None:
            raise AssessmentAttemptNotFoundError
        definition = self.definitions.get_by_id(attempt.assessment_definition_id)
        if definition is None:
            raise AssessmentAttemptNotFoundError
        return AssessmentAttemptContext(attempt, definition.activity_id)

    def _get(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
    ) -> AssessmentAttempt:
        definition = self.definitions.get(definition_id, activity_id)
        value = self.attempts.get_owned(attempt_id, definition_id, student_id)
        if definition is None or value is None:
            raise AssessmentAttemptNotFoundError
        return value


class AssessmentAttemptDetailService:
    def __init__(
        self,
        attempts: AssessmentAttemptService,
        results: AssessmentResultRepository,
    ) -> None:
        self.attempts = attempts
        self.results = results

    def from_attempt(self, attempt: AssessmentAttempt) -> AssessmentAttemptDetail:
        result = None
        if attempt.status is AssessmentAttemptStatus.REVIEWED:
            result = self.results.get_by_attempt(attempt.id)
            if result is None:
                raise AssessmentAttemptResultMissingError

        return AssessmentAttemptDetail(
            id=attempt.id,
            assessment_definition_id=attempt.assessment_definition_id,
            submission=attempt.submission,
            status=attempt.status,
            result=result,
        )

    def get_owned(
        self, attempt_id: UUID, student_id: UUID
    ) -> AssessmentAttemptDetailContext:
        context = self.attempts.resolve_owned(attempt_id, student_id)
        return AssessmentAttemptDetailContext(
            self.from_attempt(context.attempt),
            context.activity_id,
        )
