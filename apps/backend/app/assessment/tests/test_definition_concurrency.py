import threading
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.assessment.application.services import AssessmentDefinitionAlreadyExistsError
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure.models import AssessmentDefinitionModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.core.database import Base


def test_concurrent_create_preserves_one_definition_per_activity(tmp_path):
    db_path = tmp_path / "assessment-concurrency.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    activity_id = uuid4()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def create_once() -> None:
        with Session(engine) as db:
            repository = SqlAlchemyAssessmentDefinitionRepository(db)
            try:
                barrier.wait()
                repository.add(AssessmentDefinition.create(activity_id, "concurrent"))
                db.commit()
                outcomes.append("created")
            except AssessmentDefinitionAlreadyExistsError:
                db.rollback()
                outcomes.append("duplicate")

    threads = [threading.Thread(target=create_once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with Session(engine) as db:
        count = db.scalar(
            select(func.count()).select_from(AssessmentDefinitionModel)
        )
    assert count == 1
    assert sorted(outcomes) == ["created", "duplicate"]
