from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.application.ports import AssessmentAttemptRepository
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


class FailingAttemptUpdateRepository:
    def __init__(self, delegate: SqlAlchemyAssessmentAttemptRepository) -> None:
        self.delegate = delegate

    def get(self, attempt_id, definition_id):
        return self.delegate.get(attempt_id, definition_id)

    def update(self, attempt):
        raise RuntimeError("attempt update failed")


def create_schema():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def test_review_atomically_commits_one_result_and_reviewed_attempt():
    engine = create_schema()
    activity_id = uuid4()
    with Session(engine) as db, db.begin():
        definitions = SqlAlchemyAssessmentDefinitionRepository(db)
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        results = SqlAlchemyAssessmentResultRepository(db)
        definition = definitions.add(AssessmentDefinition.create(activity_id, None))
        attempt = attempts.add(
            AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
        )
        result = AssessmentResultService(results, attempts, definitions).review(
            attempt.id, definition.id, activity_id
        )

    with Session(engine) as db:
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        results = SqlAlchemyAssessmentResultRepository(db)
        stored_attempt = attempts.get(attempt.id, definition.id)
        assert stored_attempt is not None
        assert stored_attempt.status is AssessmentAttemptStatus.REVIEWED
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


def test_review_transaction_rolls_back_result_when_attempt_update_fails():
    engine = create_schema()
    activity_id = uuid4()
    with Session(engine) as db, db.begin():
        definitions = SqlAlchemyAssessmentDefinitionRepository(db)
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        definition = definitions.add(AssessmentDefinition.create(activity_id, None))
        attempt = attempts.add(
            AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
        )

    with Session(engine) as db:
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        service = AssessmentResultService(
            SqlAlchemyAssessmentResultRepository(db),
            cast(
                AssessmentAttemptRepository,
                FailingAttemptUpdateRepository(attempts),
            ),
            SqlAlchemyAssessmentDefinitionRepository(db),
        )
        with pytest.raises(RuntimeError, match="attempt update failed"), db.begin():
            service.review(attempt.id, definition.id, activity_id)

    with Session(engine) as db:
        stored_attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt.id, definition.id
        )
        assert stored_attempt is not None
        assert stored_attempt.status is AssessmentAttemptStatus.SUBMITTED
        assert SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt.id) is None
