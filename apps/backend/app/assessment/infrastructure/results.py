from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment.application.results import AssessmentResultNotFoundError
from app.assessment.domain.results import AssessmentResult
from app.assessment.infrastructure.models import AssessmentResultModel


def _domain(model: AssessmentResultModel) -> AssessmentResult:
    return AssessmentResult(
        model.id,
        model.attempt_id,
        model.score,
        model.max_score,
        model.feedback,
    )


class SqlAlchemyAssessmentResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, result: AssessmentResult) -> AssessmentResult:
        model = AssessmentResultModel(
            id=result.id,
            attempt_id=result.attempt_id,
            score=result.score,
            max_score=result.max_score,
            feedback=result.feedback,
        )
        self.db.add(model)
        self.db.flush()
        return _domain(model)

    def get(self, result_id: UUID, attempt_id: UUID) -> AssessmentResult | None:
        model = self.db.scalar(
            select(AssessmentResultModel).where(
                AssessmentResultModel.id == result_id,
                AssessmentResultModel.attempt_id == attempt_id,
            )
        )
        return _domain(model) if model else None

    def get_by_attempt(self, attempt_id: UUID) -> AssessmentResult | None:
        model = self.db.scalar(
            select(AssessmentResultModel).where(AssessmentResultModel.attempt_id == attempt_id)
        )
        return _domain(model) if model else None

    def update(self, result: AssessmentResult) -> AssessmentResult:
        model = self.db.get(AssessmentResultModel, result.id)
        if model is None or model.attempt_id != result.attempt_id:
            raise AssessmentResultNotFoundError
        model.score = result.score
        model.feedback = result.feedback
        self.db.flush()
        return _domain(model)
