from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.application.ports import AssessmentAttemptRepository
from app.assessment.application.results import AssessmentResultService
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


def test_review_and_correction_persist_one_scored_result():
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
        service = AssessmentResultService(results, attempts, definitions)
        result = service.review(
            attempt.id,
            definition.id,
            activity_id,
            4,
            10,
            "Initial",
        )
        corrected = service.correct(
            result.id,
            attempt.id,
            definition.id,
            activity_id,
            8,
            " ",
        )

    with Session(engine) as db:
        attempts = SqlAlchemyAssessmentAttemptRepository(db)
        results = SqlAlchemyAssessmentResultRepository(db)
        stored_attempt = attempts.get(attempt.id, definition.id)
        assert stored_attempt is not None
        assert stored_attempt.status is AssessmentAttemptStatus.REVIEWED
        assert results.get_by_attempt(attempt.id) == corrected
        assert corrected.id == result.id
        assert corrected.attempt_id == result.attempt_id
        assert corrected.max_score == result.max_score == 10
        assert corrected.score == 8
        assert corrected.feedback is None
        assert db.scalar(select(func.count()).select_from(AssessmentResultModel)) == 1
        with pytest.raises(IntegrityError):
            results.add(AssessmentResult.create(attempt.id, 8, 10))

    table = Base.metadata.tables["assessment_results"]
    assert set(table.c.keys()) == {
        "id",
        "attempt_id",
        "score",
        "max_score",
        "feedback",
    }
    assert not table.c.score.nullable
    assert not table.c.max_score.nullable
    assert table.c.feedback.nullable
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "assessment_attempts.id"
    }
    assert any(
        constraint.name == "uq_assessment_results_attempt"
        for constraint in table.constraints
    )
    check_constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_constraints == {
        "ck_assessment_results_max_score_positive",
        "ck_assessment_results_score_range",
    }


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
            service.review(attempt.id, definition.id, activity_id, 7, 10)

    with Session(engine) as db:
        stored_attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt.id, definition.id
        )
        assert stored_attempt is not None
        assert stored_attempt.status is AssessmentAttemptStatus.SUBMITTED
        assert SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt.id) is None
