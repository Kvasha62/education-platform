from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment.application.attempts import AssessmentAttemptNotFoundError
from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.infrastructure.models import AssessmentAttemptModel


def _domain(m):
    return AssessmentAttempt(
        m.id, m.assessment_definition_id, m.student_id, m.submission_data, m.status
    )


class SqlAlchemyAssessmentAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, a):
        m = AssessmentAttemptModel(
            id=a.id,
            assessment_definition_id=a.assessment_definition_id,
            student_id=a.student_id,
            submission_data=a.submission_data,
            status=a.status,
        )
        self.db.add(m)
        self.db.flush()
        return _domain(m)

    def get(self, i, d):
        m = self.db.scalar(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.id == i,
                AssessmentAttemptModel.assessment_definition_id == d,
            )
        )
        return _domain(m) if m else None

    def get_owned(self, i, d, s):
        m = self.db.scalar(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.id == i,
                AssessmentAttemptModel.assessment_definition_id == d,
                AssessmentAttemptModel.student_id == s,
            )
        )
        return _domain(m) if m else None

    def update(self, a):
        m = self.db.get(AssessmentAttemptModel, a.id)
        if m is None:
            raise AssessmentAttemptNotFoundError
        m.submission_data, m.status = a.submission_data, a.status
        self.db.flush()
        return _domain(m)

    def list_owned(self, d, s):
        return [
            _domain(m)
            for m in self.db.scalars(
                select(AssessmentAttemptModel).where(
                    AssessmentAttemptModel.assessment_definition_id == d,
                    AssessmentAttemptModel.student_id == s,
                )
            ).all()
        ]
