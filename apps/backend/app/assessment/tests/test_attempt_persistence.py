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


def test_attempt_persistence_allows_multiple_attempts():
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        definition = SqlAlchemyAssessmentDefinitionRepository(db).add(
            AssessmentDefinition.create(uuid4(), None)
        )
        repo = SqlAlchemyAssessmentAttemptRepository(db)
        student = uuid4()
        first = repo.add(AssessmentAttempt.create(definition.id, student, "one"))
        second = repo.add(AssessmentAttempt.create(definition.id, student, "two"))
        assert first.id != second.id and len(repo.list_owned(definition.id, student)) == 2
    table = Base.metadata.tables["assessment_attempts"]
    assert {fk.target_fullname for fk in table.foreign_keys} == {"assessment_definitions.id"}
    assert not table.c.student_id.foreign_keys
