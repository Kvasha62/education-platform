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
from app.assessment.infrastructure.models import (
    AssessmentAttemptModel,
    AssessmentResultModel,
)
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
from app.teacher_space.api.dependencies import get_teacher_assessment_review_service
from app.teacher_space.domain.models import TeacherSpace
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository

ReviewContext = tuple[UUID, UUID, UUID, UUID, UUID]


class FailingResultCreationRepository:
    def __init__(self, delegate: SqlAlchemyAssessmentResultRepository) -> None:
        self.delegate = delegate

    def add(self, result: AssessmentResult) -> AssessmentResult:
        self.delegate.add(result)
        raise RuntimeError("result creation failed")

    def get(self, result_id: UUID, attempt_id: UUID) -> AssessmentResult | None:
        return self.delegate.get(result_id, attempt_id)

    def get_by_attempt(self, attempt_id: UUID) -> AssessmentResult | None:
        return self.delegate.get_by_attempt(attempt_id)

    def update(self, result: AssessmentResult) -> AssessmentResult:
        return self.delegate.update(result)


class FailingResultUpdateRepository:
    def __init__(self, delegate: SqlAlchemyAssessmentResultRepository) -> None:
        self.delegate = delegate

    def add(self, result: AssessmentResult) -> AssessmentResult:
        return self.delegate.add(result)

    def get(self, result_id: UUID, attempt_id: UUID) -> AssessmentResult | None:
        return self.delegate.get(result_id, attempt_id)

    def get_by_attempt(self, attempt_id: UUID) -> AssessmentResult | None:
        return self.delegate.get_by_attempt(attempt_id)

    def update(self, result: AssessmentResult) -> AssessmentResult:
        self.delegate.update(result)
        raise RuntimeError("result correction failed")


def create_schema():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def seed_submitted_attempt(db: Session) -> ReviewContext:
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


def assert_reviewed_once(db: Session, attempt_id: UUID) -> AssessmentResult:
    attempt = db.scalar(
        select(AssessmentAttemptModel).where(AssessmentAttemptModel.id == attempt_id)
    )
    assert attempt is not None
    assert attempt.status is AssessmentAttemptStatus.REVIEWED
    result = SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt_id)
    assert result is not None
    assert db.scalar(select(func.count()).select_from(AssessmentResultModel)) == 1
    return result


def test_production_composition_joins_request_transaction_after_authentication():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, _definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        # Simulate authentication/authorization reads already using the request Session.
        assert db.scalar(select(func.count()).select_from(IdentityModel)) >= 1
        assert db.in_transaction()

        first_result = get_teacher_assessment_review_service(db).review(
            owner_id,
            space_id,
            activity_id,
            attempt_id,
            7,
            10,
            "Good work",
        )
        db.commit()

    with Session(engine) as db:
        stored = assert_reviewed_once(db, attempt_id)
        assert stored == first_result
        assert stored.score == 7
        assert stored.max_score == 10
        assert stored.feedback == "Good work"


def test_production_composition_denies_repeated_review_without_partial_state():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, _definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        first = get_teacher_assessment_review_service(db).review(
            owner_id,
            space_id,
            activity_id,
            attempt_id,
            7,
            10,
        )
        db.commit()

    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(IdentityModel)) >= 1
        assert db.in_transaction()
        with pytest.raises(AssessmentAttemptImmutableError):
            get_teacher_assessment_review_service(db).review(
                owner_id,
                space_id,
                activity_id,
                attempt_id,
                8,
                10,
            )
        db.rollback()

    with Session(engine) as db:
        stored = assert_reviewed_once(db, attempt_id)
        assert stored == first
        assert stored.score == 7


def test_production_composition_corrects_existing_result_atomically():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, _definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        original = get_teacher_assessment_review_service(db).review(
            owner_id,
            space_id,
            activity_id,
            attempt_id,
            4,
            10,
            "Initial",
        )
        db.commit()

    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(IdentityModel)) >= 1
        assert db.in_transaction()
        corrected = get_teacher_assessment_review_service(db).correct(
            owner_id,
            space_id,
            activity_id,
            attempt_id,
            original.id,
            8,
            "   ",
        )
        db.commit()

    with Session(engine) as db:
        stored = assert_reviewed_once(db, attempt_id)
        assert stored == corrected
        assert corrected.id == original.id
        assert corrected.attempt_id == original.attempt_id
        assert corrected.max_score == original.max_score == 10
        assert corrected.score == 8
        assert corrected.feedback is None
        assert db.scalar(select(func.count()).select_from(AssessmentAttemptModel)) == 1


def test_production_composition_rolls_back_failed_result_creation():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(IdentityModel)) >= 1
        assert db.in_transaction()
        service = get_teacher_assessment_review_service(db)
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
                attempt_id,
                7,
                10,
            )
        db.rollback()

    with Session(engine) as db:
        attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt_id, definition_id
        )
        assert attempt is not None
        assert attempt.status is AssessmentAttemptStatus.SUBMITTED
        assert SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt_id) is None


def test_production_composition_rolls_back_failed_result_correction():
    engine = create_schema()
    with Session(engine) as db, db.begin():
        owner_id, space_id, activity_id, definition_id, attempt_id = (
            seed_submitted_attempt(db)
        )

    with Session(engine) as db:
        original = get_teacher_assessment_review_service(db).review(
            owner_id,
            space_id,
            activity_id,
            attempt_id,
            4,
            10,
            "Initial",
        )
        db.commit()

    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(IdentityModel)) >= 1
        assert db.in_transaction()
        service = get_teacher_assessment_review_service(db)
        service.results.results = cast(
            AssessmentResultRepository,
            FailingResultUpdateRepository(
                cast(SqlAlchemyAssessmentResultRepository, service.results.results)
            ),
        )
        with pytest.raises(RuntimeError, match="result correction failed"):
            service.correct(
                owner_id,
                space_id,
                activity_id,
                attempt_id,
                original.id,
                9,
                "Changed",
            )
        db.rollback()

    with Session(engine) as db:
        attempt = SqlAlchemyAssessmentAttemptRepository(db).get(
            attempt_id, definition_id
        )
        assert attempt is not None
        assert attempt.status is AssessmentAttemptStatus.REVIEWED
        stored = SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt_id)
        assert stored == original
        assert db.scalar(select(func.count()).select_from(AssessmentResultModel)) == 1
