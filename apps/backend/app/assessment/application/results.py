from uuid import UUID

from app.assessment.application.attempts import AssessmentAttemptNotFoundError
from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
    AssessmentResultRepository,
)
from app.assessment.domain.attempts import AssessmentAttempt, AssessmentAttemptStatus
from app.assessment.domain.results import AssessmentResult


class AssessmentResultAlreadyExistsError(Exception):
    pass


class AssessmentResultNotFoundError(Exception):
    pass


class AssessmentResultService:
    def __init__(
        self,
        results: AssessmentResultRepository,
        attempts: AssessmentAttemptRepository,
        definitions: AssessmentDefinitionRepository,
    ) -> None:
        self.results = results
        self.attempts = attempts
        self.definitions = definitions

    def review(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        score: int,
        max_score: int,
        feedback: str | None = None,
    ) -> AssessmentResult:
        reviewed_attempt = self._get_attempt(attempt_id, definition_id, activity_id).review()
        if self.results.get_by_attempt(attempt_id) is not None:
            raise AssessmentResultAlreadyExistsError
        result = self.results.add(
            AssessmentResult.create(attempt_id, score, max_score, feedback)
        )
        self.attempts.update(reviewed_attempt)
        return result

    def correct(
        self,
        result_id: UUID,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        score: int,
        feedback: str | None,
    ) -> AssessmentResult:
        attempt = self._get_attempt(attempt_id, definition_id, activity_id)
        result = self.results.get(result_id, attempt_id)
        if attempt.status is not AssessmentAttemptStatus.REVIEWED or result is None:
            raise AssessmentResultNotFoundError
        return self.results.update(result.correct(score, feedback))

    def _get_attempt(
        self, attempt_id: UUID, definition_id: UUID, activity_id: UUID
    ) -> AssessmentAttempt:
        definition = self.definitions.get(definition_id, activity_id)
        attempt = self.attempts.get(attempt_id, definition_id)
        if definition is None or attempt is None:
            raise AssessmentAttemptNotFoundError
        return attempt
