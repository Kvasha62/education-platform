from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure import models as assessment_models  # noqa:F401
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.core.database import Base


def test_attempt_persistence_uses_submission_contract_and_allows_multiple_attempts():
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        definition = SqlAlchemyAssessmentDefinitionRepository(db).add(
            AssessmentDefinition.create(uuid4(), None)
        )
        repository = SqlAlchemyAssessmentAttemptRepository(db)
        student_id = uuid4()
        first = repository.add(
            AssessmentAttempt.create(definition.id, student_id, "answer")
        )
        second = repository.add(
            AssessmentAttempt.create(definition.id, student_id, "   ")
        )
        cleared = repository.update(first.update_submission(None))

        assert first.id != second.id
        assert second.submission is None
        assert cleared.submission is None
        assert len(repository.list_owned(definition.id, student_id)) == 2

    table = Base.metadata.tables["assessment_attempts"]
    assert "submission" in table.c
    assert "submission_data" not in table.c
    assert table.c.submission.nullable
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "assessment_definitions.id"
    }
    assert not table.c.student_id.foreign_keys
