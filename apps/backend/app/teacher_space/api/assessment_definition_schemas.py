"""Pydantic contracts for the Teacher AssessmentDefinition management API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.assessment.domain.models import AssessmentDefinition, AssessmentDefinitionStatus


class CreateAssessmentDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str | None


class UpdateAssessmentDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str | None


class AssessmentDefinitionResponse(BaseModel):
    id: UUID
    activity_id: UUID
    instructions: str | None
    status: AssessmentDefinitionStatus

    @classmethod
    def from_definition(
        cls, definition: AssessmentDefinition
    ) -> "AssessmentDefinitionResponse":
        return cls(
            id=definition.id,
            activity_id=definition.activity_id,
            instructions=definition.instructions,
            status=definition.status,
        )
