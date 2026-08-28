"""Pydantic contracts for the Teacher AssessmentDefinition management API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.assessment.domain.models import AssessmentDefinition, AssessmentDefinitionStatus


class CreateAssessmentDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str | None


class UpdateAssessmentDefinitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str | None = None

    @model_validator(mode="after")
    def instructions_must_be_present(self) -> "UpdateAssessmentDefinitionRequest":
        if "instructions" not in self.model_fields_set:
            raise ValueError("instructions is required")
        return self


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
