from uuid import UUID

from app.assessment.application.ports import AssessmentDefinitionRepository
from app.assessment.domain.models import AssessmentDefinition


class AssessmentDefinitionAlreadyExistsError(Exception):
    pass


class AssessmentDefinitionNotFoundError(Exception):
    pass


class AssessmentDefinitionService:
    def __init__(self, repository: AssessmentDefinitionRepository) -> None:
        self.repository = repository

    def create(self, activity_id: UUID, instructions: str | None) -> AssessmentDefinition:
        if self.repository.get_by_activity(activity_id) is not None:
            raise AssessmentDefinitionAlreadyExistsError
        return self.repository.add(AssessmentDefinition.create(activity_id, instructions))

    def get(self, activity_id: UUID) -> AssessmentDefinition:
        definition = self.repository.get_by_activity(activity_id)
        if definition is None:
            raise AssessmentDefinitionNotFoundError
        return definition

    def update_instructions(
        self, definition_id: UUID, activity_id: UUID, instructions: str | None
    ) -> AssessmentDefinition:
        definition = self._get(definition_id, activity_id)
        return self.repository.update(definition.update_instructions(instructions))

    def archive(self, definition_id: UUID, activity_id: UUID) -> AssessmentDefinition:
        return self.repository.update(self._get(definition_id, activity_id).archive())

    def _get(self, definition_id: UUID, activity_id: UUID) -> AssessmentDefinition:
        definition = self.repository.get(definition_id, activity_id)
        if definition is None:
            raise AssessmentDefinitionNotFoundError
        return definition
