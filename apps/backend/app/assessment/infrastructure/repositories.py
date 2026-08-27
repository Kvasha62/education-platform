from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assessment.application.services import (
    AssessmentDefinitionAlreadyExistsError,
    AssessmentDefinitionNotFoundError,
)
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure.models import AssessmentDefinitionModel


def _domain(model: AssessmentDefinitionModel) -> AssessmentDefinition:
    return AssessmentDefinition(model.id, model.activity_id, model.instructions, model.status)


class SqlAlchemyAssessmentDefinitionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, definition: AssessmentDefinition) -> AssessmentDefinition:
        model = AssessmentDefinitionModel(
            id=definition.id,
            activity_id=definition.activity_id,
            instructions=definition.instructions,
            status=definition.status,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise AssessmentDefinitionAlreadyExistsError from error
        return _domain(model)

    def get(self, definition_id: UUID, activity_id: UUID) -> AssessmentDefinition | None:
        model = self.db.scalar(
            select(AssessmentDefinitionModel).where(
                AssessmentDefinitionModel.id == definition_id,
                AssessmentDefinitionModel.activity_id == activity_id,
            )
        )
        return _domain(model) if model else None

    def get_by_activity(self, activity_id: UUID) -> AssessmentDefinition | None:
        model = self.db.scalar(
            select(AssessmentDefinitionModel).where(
                AssessmentDefinitionModel.activity_id == activity_id
            )
        )
        return _domain(model) if model else None

    def update(self, definition: AssessmentDefinition) -> AssessmentDefinition:
        model = self.db.get(AssessmentDefinitionModel, definition.id)
        if model is None:
            raise AssessmentDefinitionNotFoundError
        model.instructions, model.status = definition.instructions, definition.status
        self.db.flush()
        return _domain(model)
