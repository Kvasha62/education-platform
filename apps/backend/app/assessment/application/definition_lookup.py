from typing import Protocol
from uuid import UUID

from app.assessment.application.ports import AssessmentDefinitionRepository


class AssessmentDefinitionIdLookup(Protocol):
    def get_id_for_activity(self, activity_id: UUID) -> UUID | None: ...


class AssessmentDefinitionIdLookupService:
    def __init__(self, definitions: AssessmentDefinitionRepository) -> None:
        self.definitions = definitions

    def get_id_for_activity(self, activity_id: UUID) -> UUID | None:
        definition = self.definitions.get_by_activity(activity_id)
        return None if definition is None else definition.id
