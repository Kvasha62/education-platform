from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.application.services import AssessmentDefinitionAlreadyExistsError
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure import models as assessment_models  # noqa: F401
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.core.database import Base


def test_persistence_and_unique_activity():
    engine = create_engine("sqlite+pysqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    activity_id = uuid4()
    with Session(engine) as db:
        repo = SqlAlchemyAssessmentDefinitionRepository(db)
        saved = repo.add(AssessmentDefinition.create(activity_id, "initial"))
        saved = repo.update(saved.update_instructions("changed"))
        assert repo.get(saved.id, activity_id) == saved
        with pytest.raises(AssessmentDefinitionAlreadyExistsError):
            repo.add(AssessmentDefinition.create(activity_id, None))
    table = Base.metadata.tables["assessment_definitions"]
    assert not table.c.activity_id.foreign_keys
    assert any(c.name == "uq_assessment_definitions_activity" for c in table.constraints)
