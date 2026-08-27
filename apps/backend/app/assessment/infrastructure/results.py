from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assessment.application.results import AssessmentResultAlreadyExistsError
from app.assessment.domain.results import AssessmentResult
from app.assessment.infrastructure.models import AssessmentResultModel


def _domain(model: AssessmentResultModel) -> AssessmentResult:
    return AssessmentResult(model.id, model.attempt_id)


class SqlAlchemyAssessmentResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, result: AssessmentResult) -> AssessmentResult:
        model = AssessmentResultModel(id=result.id, attempt_id=result.attempt_id)
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise AssessmentResultAlreadyExistsError from error
        return _domain(model)

    def get_by_attempt(self, attempt_id: UUID) -> AssessmentResult | None:
        model = self.db.scalar(
            select(AssessmentResultModel).where(AssessmentResultModel.attempt_id == attempt_id)
        )
        return _domain(model) if model else None
