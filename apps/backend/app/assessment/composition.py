"""Assessment-owned composition for cross-context application use cases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.application.attempts import (
    AssessmentAttemptDetailService,
    AssessmentAttemptService,
)
from app.assessment.application.definition_lookup import (
    AssessmentDefinitionIdLookup,
    AssessmentDefinitionIdLookupService,
)
from app.assessment.application.results import AssessmentResultService
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.database import get_db


def get_assessment_definition_id_lookup(
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentDefinitionIdLookup:
    return AssessmentDefinitionIdLookupService(
        SqlAlchemyAssessmentDefinitionRepository(db)
    )


def get_assessment_attempt_service(
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentAttemptService:
    return AssessmentAttemptService(
        SqlAlchemyAssessmentAttemptRepository(db),
        SqlAlchemyAssessmentDefinitionRepository(db),
    )


def get_assessment_attempt_detail_service(
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentAttemptDetailService:
    return AssessmentAttemptDetailService(
        get_assessment_attempt_service(db),
        SqlAlchemyAssessmentResultRepository(db),
    )


def get_assessment_result_service(
    db: Annotated[Session, Depends(get_db)],
) -> AssessmentResultService:
    return AssessmentResultService(
        SqlAlchemyAssessmentResultRepository(db),
        SqlAlchemyAssessmentAttemptRepository(db),
        SqlAlchemyAssessmentDefinitionRepository(db),
    )
