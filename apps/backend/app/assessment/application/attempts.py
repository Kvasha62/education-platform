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


@dataclass(frozen=True, slots=True)
class AssessmentAttemptDetail:
    id: UUID
    assessment_definition_id: UUID
    submission: str | None
    status: AssessmentAttemptStatus
    result: AssessmentResult | None


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
        if definition is None or definition.status is not AssessmentDefinitionStatus.ACTIVE:
            raise AssessmentDefinitionUnavailableError
        return self.attempts.add(
            AssessmentAttempt.create(definition_id, student_id, submission)
        )

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
        attempts: AssessmentAttemptRepository,
        definitions: AssessmentDefinitionRepository,
        results: AssessmentResultRepository,
    ) -> None:
        self.attempts = attempts
        self.definitions = definitions
        self.results = results

    def get_owned(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
    ) -> AssessmentAttemptDetail:
        definition = self.definitions.get(definition_id, activity_id)
        attempt = self.attempts.get_owned(attempt_id, definition_id, student_id)
        if definition is None or attempt is None:
            raise AssessmentAttemptNotFoundError

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
