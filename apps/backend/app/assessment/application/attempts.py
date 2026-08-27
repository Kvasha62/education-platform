from uuid import UUID

from app.assessment.application.ports import (
    AssessmentAttemptRepository,
    AssessmentDefinitionRepository,
)
from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.domain.models import AssessmentDefinitionStatus


class AssessmentAttemptNotFoundError(Exception):
    pass


class AssessmentDefinitionUnavailableError(Exception):
    pass


class AssessmentAttemptService:
    def __init__(
        self, attempts: AssessmentAttemptRepository, definitions: AssessmentDefinitionRepository
    ):
        self.attempts, self.definitions = attempts, definitions

    def create(self, definition_id: UUID, activity_id: UUID, student_id: UUID, data: str | None):
        definition = self.definitions.get(definition_id, activity_id)
        if definition is None or definition.status is not AssessmentDefinitionStatus.ACTIVE:
            raise AssessmentDefinitionUnavailableError
        return self.attempts.add(AssessmentAttempt.create(definition_id, student_id, data))

    def update_submission(
        self,
        attempt_id: UUID,
        definition_id: UUID,
        activity_id: UUID,
        student_id: UUID,
        data: str | None,
    ):
        return self.attempts.update(
            self._get(attempt_id, definition_id, activity_id, student_id).update_submission(data)
        )

    def submit(self, attempt_id: UUID, definition_id: UUID, activity_id: UUID, student_id: UUID):
        return self.attempts.update(
            self._get(attempt_id, definition_id, activity_id, student_id).submit()
        )

    def get(self, attempt_id: UUID, definition_id: UUID, activity_id: UUID, student_id: UUID):
        return self._get(attempt_id, definition_id, activity_id, student_id)

    def _get(self, attempt_id, definition_id, activity_id, student_id):
        definition = self.definitions.get(definition_id, activity_id)
        value = self.attempts.get_owned(attempt_id, definition_id, student_id)
        if definition is None or value is None:
            raise AssessmentAttemptNotFoundError
        return value
