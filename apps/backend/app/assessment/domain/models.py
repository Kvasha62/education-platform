from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID, uuid4


class AssessmentDefinitionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AssessmentDefinitionImmutableError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AssessmentDefinition:
    id: UUID
    activity_id: UUID
    instructions: str | None
    status: AssessmentDefinitionStatus

    @classmethod
    def create(cls, activity_id: UUID, instructions: str | None) -> "AssessmentDefinition":
        return cls(uuid4(), activity_id, instructions, AssessmentDefinitionStatus.ACTIVE)

    def update_instructions(self, instructions: str | None) -> "AssessmentDefinition":
        if self.status is AssessmentDefinitionStatus.ARCHIVED:
            raise AssessmentDefinitionImmutableError
        return replace(self, instructions=instructions)

    def archive(self) -> "AssessmentDefinition":
        if self.status is AssessmentDefinitionStatus.ARCHIVED:
            raise AssessmentDefinitionImmutableError
        return replace(self, status=AssessmentDefinitionStatus.ARCHIVED)
