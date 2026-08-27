from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment.application.attempts import AssessmentAttemptNotFoundError
from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.infrastructure.models import AssessmentAttemptModel


def _domain(model: AssessmentAttemptModel) -> AssessmentAttempt:
    return AssessmentAttempt(
        model.id,
        model.assessment_definition_id,
        model.student_id,
        model.submission,
        model.status,
    )


class SqlAlchemyAssessmentAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        model = AssessmentAttemptModel(
            id=attempt.id,
            assessment_definition_id=attempt.assessment_definition_id,
            student_id=attempt.student_id,
            submission=attempt.submission,
            status=attempt.status,
        )
        self.db.add(model)
        self.db.flush()
        return _domain(model)

    def get(
        self, attempt_id, definition_id
    ) -> AssessmentAttempt | None:
        model = self.db.scalar(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.id == attempt_id,
                AssessmentAttemptModel.assessment_definition_id == definition_id,
            )
        )
        return _domain(model) if model else None

    def get_owned(
        self, attempt_id, definition_id, student_id
    ) -> AssessmentAttempt | None:
        model = self.db.scalar(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.id == attempt_id,
                AssessmentAttemptModel.assessment_definition_id == definition_id,
                AssessmentAttemptModel.student_id == student_id,
            )
        )
        return _domain(model) if model else None

    def update(self, attempt: AssessmentAttempt) -> AssessmentAttempt:
        model = self.db.get(AssessmentAttemptModel, attempt.id)
        if model is None:
            raise AssessmentAttemptNotFoundError
        model.submission = attempt.submission
        model.status = attempt.status
        self.db.flush()
        return _domain(model)

    def list_owned(self, definition_id, student_id) -> list[AssessmentAttempt]:
        return [
            _domain(model)
            for model in self.db.scalars(
                select(AssessmentAttemptModel).where(
                    AssessmentAttemptModel.assessment_definition_id == definition_id,
                    AssessmentAttemptModel.student_id == student_id,
                )
            ).all()
        ]
