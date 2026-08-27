from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment.application.ports import AssessmentResultRepository
from app.assessment.domain.attempts import (
    AssessmentAttempt,
    AssessmentAttemptImmutableError,
    AssessmentAttemptStatus,
)
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.domain.results import AssessmentResult
from app.assessment.infrastructure import models as assessment_models  # noqa: F401
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.models import AssessmentResultModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.database import Base
from app.education.domain.models import (
    Activity,
    ActivityType,
    Course,
    EducationalEnvironment,
    LearningUnit,
    Section,
)
from app.education.infrastructure.repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEnvironmentRepository,
    SqlAlchemyLearningUnitRepository,
    SqlAlchemySectionRepository,
)
from app.identity.domain.models import IdentityStatus
from app.identity.infrastructure.models import IdentityModel
from app.teacher_space.api.dependencies import get_teacher_assessment_result_service
from app.teacher_space.domain.models import TeacherSpace
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository


class FailingResultCreationRepository:
    def __init__(self, delegate: SqlAlchemyAssessmentResultRepository) -> None:
        self.delegate = delegate

    def add(self, result: AssessmentResult) -> AssessmentResult:
        self.delegate.add(result)
        raise RuntimeError("result creation failed")

    def get_by_attempt(self, attempt_id: UUID) -> AssessmentResult | None:
        return self.delegate.get_by_attempt(attempt_id)


def create_schema():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def seed_submitted_attempt(db: Session):
    owner_id = uuid4()
    now = datetime.now(UTC)
    db.add(
        IdentityModel(
            id=owner_id,
            email=f"{owner_id}@example.com",
            password_hash="hash",
            status=IdentityStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    teacher_space = SqlAlchemyTeacherSpaceRepository(db).add(
        TeacherSpace.create(owner_id, "Space")
    )
    environment = SqlAlchemyEnvironmentRepository(db).add(
        EducationalEnvironment.create(teacher_space.id, "Environment")
    )
    course = SqlAlchemyCourseRepository(db).add(Course.create(environment.id, "Course"))
    section = SqlAlchemySectionRepository(db).add(Section.create(course.id, "Section", 0))
    unit = SqlAlchemyLearningUnitRepository(db).add(
        LearningUnit.create(section.id, "Unit", 0)
    )
    activity = SqlAlchemyActivityRepository(db).add(
        Activity.create(unit.id, "Homework", ActivityType.HOMEWORK, 0)
    )
    definition = SqlAlchemyAssessmentDefinitionRepository(db).add(
        AssessmentDefinition.create(activity.id, None)
    )
    attempt = SqlAlchemyAssessmentAttemptRepository(db).add(
        AssessmentAttempt.create(definition.id, uuid4(), "answer").submit()
    )
    return owner_id, teacher_space.id, activity.id, definition.id, attempt.id


def test_production_composition_commits_review_and_denies_repeated_review():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        first_result = get_teacher_assessment_result_service(db).review(
            owner_id,
            space_id,
            activity_id,
            definition_id,
            attempt_id,
        )
        assert not db.in_transaction()

    with Session(engine) as db:
        with pytest.raises(AssessmentAttemptImmutableError):
            get_teacher_assessment_result_service(db).review(
                owner_id,
                space_id,
                activity_id,
                definition_id,
                attempt_id,
            )
        assert not db.in_transaction()

    with Session(engine) as db:
        attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt_id, definition_id
        )
        assert attempt is not None
        assert attempt.status is AssessmentAttemptStatus.REVIEWED
        assert SqlAlchemyAssessmentResultRepository(db).get_by_attempt(
            attempt_id
        ) == first_result
        assert db.scalar(select(func.count()).select_from(AssessmentResultModel)) == 1


def test_production_composition_rolls_back_failed_result_creation():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        service = get_teacher_assessment_result_service(db)
        service.results.results = cast(
            AssessmentResultRepository,
            FailingResultCreationRepository(
                cast(SqlAlchemyAssessmentResultRepository, service.results.results)
            ),
        )
        with pytest.raises(RuntimeError, match="result creation failed"):
            service.review(
                owner_id,
                space_id,
                activity_id,
                definition_id,
                attempt_id,
            )
        assert not db.in_transaction()

    with Session(engine) as db:
        attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt_id, definition_id
        )
        assert attempt is not None
        assert attempt.status is AssessmentAttemptStatus.SUBMITTED
        assert SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt_id) is None
