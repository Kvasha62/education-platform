"""Assessment-owned composition for cross-context application use cases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.application.results import AssessmentResultService
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.database import get_db


def get_assessment_result_service(
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentResultService:
    return AssessmentResultService(
        SqlAlchemyAssessmentResultRepository(db),
        SqlAlchemyAssessmentAttemptRepository(db),
        SqlAlchemyAssessmentDefinitionRepository(db),
    )
