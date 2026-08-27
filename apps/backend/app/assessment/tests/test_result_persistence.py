from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.application.results import (
    AssessmentResultAlreadyExistsError,
    AssessmentResultService,
)
from app.assessment.domain.attempts import AssessmentAttempt, AssessmentAttemptStatus
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.domain.results import AssessmentResult
from app.assessment.infrastructure import models as assessment_models  # noqa: F401
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.models import AssessmentResultModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.database import Base


def test_review_persists_one_result_for_attempt():
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        definitions = SqlAlchemyAssessmentDefinitionRepository(db)
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        results = SqlAlchemyAssessmentResultRepository(db)
        activity_id = uuid4()
        definition = definitions.add(AssessmentDefinition.create(activity_id, None))
        attempt = attempts.add(
            AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
        )
        service = AssessmentResultService(results, attempts, definitions)

        result = service.review(attempt.id, definition.id, activity_id)

        assert attempts.get(attempt.id, definition.id).status is AssessmentAttemptStatus.REVIEWED
        assert results.get_by_attempt(attempt.id) == result
        assert db.scalar(select(func.count()).select_from(AssessmentResultModel)) == 1
        with pytest.raises(AssessmentResultAlreadyExistsError):
            results.add(AssessmentResult.create(attempt.id))

    table = Base.metadata.tables["assessment_results"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "assessment_attempts.id"
    }
    assert any(
        constraint.name == "uq_assessment_results_attempt"
        for constraint in table.constraints
    )
