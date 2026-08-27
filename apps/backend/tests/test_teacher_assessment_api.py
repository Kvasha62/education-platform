from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.attempts import AssessmentAttempt
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.models import AssessmentAttemptModel, AssessmentResultModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
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
from app.identity.api.dependencies import SESSION_COOKIE_NAME
from app.main import app
from app.teacher_space.domain.models import TeacherSpace
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False, "autocommit": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
ORIGIN = "http://frontend.test"
HEADERS = {"Origin": ORIGIN}


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite://",
        minio_endpoint="x",
        frontend_origin=ORIGIN,
        auth_cookie_secure=False,
        auth_session_ttl_seconds=3600,
        auth_login_rate_limit=100,
        auth_register_rate_limit=100,
        auth_rate_limit_window_seconds=60,
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = settings
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def auth(client: TestClient, email: str) -> tuple[UUID, str]:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a secure password"},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a secure password"},
    )
    assert login.status_code == 200
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return UUID(registration.json()["id"]), token


def use(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)


def teacher_space(owner_id: UUID | None = None) -> tuple[UUID, UUID, UUID]:
    """Create a Teacher Space and an Activity with an Assessment Definition in it."""
    with TestingSession.begin() as db:
        space = SqlAlchemyTeacherSpaceRepository(db).add(
            TeacherSpace.create(owner_id or uuid4(), "Teacher Space")
        )
        environment = SqlAlchemyEnvironmentRepository(db).add(
            EducationalEnvironment.create(space.id, "Environment")
        )
        course = SqlAlchemyCourseRepository(db).add(Course.create(environment.id, "Course"))
        section = SqlAlchemySectionRepository(db).add(
            Section.create(course.id, "Section", 0)
        )
        unit = SqlAlchemyLearningUnitRepository(db).add(
            LearningUnit.create(section.id, "Unit", 0)
        )
        activity = SqlAlchemyActivityRepository(db).add(
            Activity.create(unit.id, "Homework", ActivityType.HOMEWORK, 0)
        )
        definition = SqlAlchemyAssessmentDefinitionRepository(db).add(
            AssessmentDefinition.create(activity.id, "Instructions")
        )
        return space.id, activity.id, definition.id


def add_submitted(definition_id: UUID, student_id: UUID | None = None) -> UUID:
    with TestingSession.begin() as db:
        return SqlAlchemyAssessmentAttemptRepository(db).add(
            AssessmentAttempt.create(
                definition_id,
                student_id or uuid4(),
                "Student answer",
            ).submit()
        ).id


def add_reviewed(
    definition_id: UUID,
    student_id: UUID | None = None,
    *,
    score: int = 8,
    max_score: int = 10,
    feedback: str | None = "Reviewed",
) -> UUID:
    with TestingSession.begin() as db:
        repository = SqlAlchemyAssessmentAttemptRepository(db)
        learner = student_id or uuid4()
        attempt = repository.add(
            AssessmentAttempt.create(definition_id, learner, "Student answer").submit()
        )
        definition = SqlAlchemyAssessmentDefinitionRepository(db).get_by_id(definition_id)
        assert definition is not None
        return AssessmentResultService(
            SqlAlchemyAssessmentResultRepository(db),
            SqlAlchemyAssessmentAttemptRepository(db),
            SqlAlchemyAssessmentDefinitionRepository(db),
        ).review(
            attempt.id,
            definition.id,
            definition.activity_id,
            score,
            max_score,
            feedback,
        ).attempt_id


def review_path(space_id: UUID, activity_id: UUID) -> str:
    return f"/api/v1/teacher-spaces/{space_id}/activities/{activity_id}/assessment-attempts"


def item_path(space_id: UUID, activity_id: UUID, attempt_id: UUID) -> str:
    return f"{review_path(space_id, activity_id)}/{attempt_id}"


def stored_status(attempt_id: UUID) -> str:
    with TestingSession() as db:
        model = db.get(AssessmentAttemptModel, attempt_id)
        assert model is not None
        return model.status.value


def stored_submission(attempt_id: UUID) -> str | None:
    with TestingSession() as db:
        model = db.get(AssessmentAttemptModel, attempt_id)
        assert model is not None
        return model.submission


def result_count() -> int:
    with TestingSession() as db:
        return db.scalar(select(func.count()).select_from(AssessmentResultModel))


def test_all_teacher_assessment_endpoints_require_authentication(client):
    space_id, activity_id, definition_id = teacher_space()
    attempt_id = add_submitted(definition_id)
    for path in (
        review_path(space_id, activity_id),
        item_path(space_id, activity_id, attempt_id),
    ):
        assert client.get(path, headers=HEADERS).status_code == 401
    for path in (
        f"{item_path(space_id, activity_id, attempt_id)}/review",
        f"{item_path(space_id, activity_id, attempt_id)}/correction",
    ):
        assert client.post(
            path,
            json={"score": 8, "max_score": 10},
            headers=HEADERS,
        ).status_code == 401


def test_collection_default_membership_status_filter_pagination_and_ordering(client):
    owner_id, token = auth(client, "queue@example.com")
    space_id, activity_id, definition_id = teacher_space(owner_id)
    student_id = uuid4()
    submitted = sorted(add_submitted(definition_id, student_id) for _ in range(3))
    reviewed = add_reviewed(definition_id, student_id)
    use(client, token)

    default = client.get(review_path(space_id, activity_id), headers=HEADERS)
    assert default.status_code == 200
    body = default.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["has_next"] is False
    ids = [item["id"] for item in body["items"]]
    assert ids == sorted(ids)
    assert set(ids) == {str(value) for value in [*submitted, reviewed]}
    assert all(item["status"] in {"submitted", "reviewed"} for item in body["items"])
    assert all(item["student_id"] == str(student_id) for item in body["items"])
    assert all(item["result"] is None for item in body["items"] if item["status"] == "submitted")
    assert len(
        [item for item in body["items"] if item["status"] == "reviewed"]
    ) == 1
    for item in body["items"]:
        assert set(item) == {
            "id",
            "student_id",
            "status",
            "assessment_definition_id",
            "activity_id",
            "result",
        }
        if item["id"] == str(reviewed):
            assert item["result"] == {
                "id": item["result"]["id"],
                "attempt_id": str(reviewed),
                "score": 8,
                "max_score": 10,
                "feedback": "Reviewed",
            }

    submitted_only = client.get(
        review_path(space_id, activity_id), params={"status": "submitted"}, headers=HEADERS
    )
    assert submitted_only.status_code == 200
    assert {item["id"] for item in submitted_only.json()["items"]} == {
        str(value) for value in submitted
    }

    reviewed_only = client.get(
        review_path(space_id, activity_id), params={"status": "reviewed"}, headers=HEADERS
    )
    assert reviewed_only.status_code == 200
    assert [item["id"] for item in reviewed_only.json()["items"]] == [str(reviewed)]

    first_page = client.get(
        review_path(space_id, activity_id),
        params={"page": 1, "page_size": 2},
        headers=HEADERS,
    )
    assert first_page.status_code == 200
    assert first_page.json()["page"] == 1
    assert first_page.json()["page_size"] == 2
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["has_next"] is True

    last_page = client.get(
        review_path(space_id, activity_id),
        params={"page": 2, "page_size": 2},
        headers=HEADERS,
    )
    assert last_page.status_code == 200
    assert last_page.json()["page"] == 2
    assert last_page.json()["page_size"] == 2
    assert len(last_page.json()["items"]) == 2
    assert last_page.json()["has_next"] is False

    beyond = client.get(
        review_path(space_id, activity_id),
        params={"page": 99, "page_size": 2},
        headers=HEADERS,
    )
    assert beyond.status_code == 200
    assert beyond.json() == {"items": [], "page": 99, "page_size": 2, "has_next": False}


@pytest.mark.parametrize(
    "params",
    [
        {"status": "draft"},
        {"status": "submitted,reviewed"},
        {"page": 0},
        {"page": -1},
        {"page": "x"},
        {"page_size": 0},
        {"page_size": 101},
        {"page_size": "x"},
    ],
)
def test_collection_rejects_invalid_page_or_status(client, params):
    space_id, activity_id, _ = teacher_space()
    _, token = auth(client, "invalid-queue@example.com")
    use(client, token)
    response = client.get(review_path(space_id, activity_id), params=params, headers=HEADERS)
    assert response.status_code == 422


def test_collection_is_isolated_to_authorized_space_and_activity(client):
    owner_id, owner_token = auth(client, "isolation@example.com")
    space_id, activity_id, definition_id = teacher_space(owner_id)
    other_space_id, other_activity_id, other_definition_id = teacher_space()
    add_submitted(definition_id)
    add_submitted(other_definition_id)
    use(client, owner_token)

    own = client.get(review_path(space_id, activity_id), headers=HEADERS)
    assert own.status_code == 200
    assert len(own.json()["items"]) == 1

    other = client.get(review_path(other_space_id, other_activity_id), headers=HEADERS)
    assert other.status_code == 403

    unknown = client.get(review_path(uuid4(), activity_id), headers=HEADERS)
    assert unknown.status_code == 404


def test_detail_returns_submission_and_complete_reviewed_result(client):
    teacher_id, token = auth(client, "detail@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    submitted_id = add_submitted(definition_id)
    reviewed_id = add_reviewed(definition_id)
    use(client, token)

    submitted = client.get(item_path(space_id, activity_id, submitted_id), headers=HEADERS)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submission"] == "Student answer"
    assert submitted.json()["result"] is None
    assert set(submitted.json()) == {
        "id",
        "student_id",
        "status",
        "assessment_definition_id",
        "activity_id",
        "submission",
        "result",
    }

    reviewed = client.get(item_path(space_id, activity_id, reviewed_id), headers=HEADERS)
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    assert reviewed.json()["submission"] == "Student answer"
    assert reviewed.json()["result"] == {
        "id": reviewed.json()["result"]["id"],
        "attempt_id": str(reviewed_id),
        "score": 8,
        "max_score": 10,
        "feedback": "Reviewed",
    }

    missing = client.get(item_path(space_id, activity_id, uuid4()), headers=HEADERS)
    assert missing.status_code == 404


def test_detail_does_not_depend_on_student_enrollment_or_progress(client):
    owner_id, token = auth(client, "no-progress@example.com")
    space_id, activity_id, definition_id = teacher_space(owner_id)
    # The student has no enrollment or ActivityProgress in the Learning context;
    # Teacher Review must still read the submission and result from Assessment.
    attempt_id = add_reviewed(
        definition_id,
        score=7,
        max_score=10,
        feedback="No progress dependency",
    )
    use(client, token)

    detail = client.get(item_path(space_id, activity_id, attempt_id), headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["submission"] == "Student answer"
    assert detail.json()["result"]["score"] == 7

    collection = client.get(review_path(space_id, activity_id), headers=HEADERS)
    assert collection.status_code == 200
    assert [item["id"] for item in collection.json()["items"]] == [str(attempt_id)]


def test_detail_scope_authorization(client):
    owner_id, owner_token = auth(client, "detail-auth@example.com")
    space_id, activity_id, definition_id = teacher_space(owner_id)
    other_space_id, other_activity_id, other_definition_id = teacher_space()
    attempt_id = add_submitted(definition_id)
    other_attempt_id = add_submitted(other_definition_id)
    use(client, owner_token)
    assert client.get(item_path(space_id, activity_id, attempt_id), headers=HEADERS).status_code == 200

    assert client.get(
        item_path(other_space_id, other_activity_id, other_attempt_id), headers=HEADERS
    ).status_code == 403

    assert client.get(item_path(uuid4(), activity_id, attempt_id), headers=HEADERS).status_code == 404


def test_reviewed_attempt_without_result_returns_500(client):
    teacher_id, token = auth(client, "invariant@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    with TestingSession.begin() as db:
        repository = SqlAlchemyAssessmentAttemptRepository(db)
        attempt = repository.add(
            AssessmentAttempt.create(definition_id, uuid4(), "answer").submit().review()
        )
        attempt_id = attempt.id
    use(client, token)

    collection = client.get(review_path(space_id, activity_id), headers=HEADERS)
    assert collection.status_code == 500

    detail = client.get(item_path(space_id, activity_id, attempt_id), headers=HEADERS)
    assert detail.status_code == 500
    assert detail.json() == {"detail": "Internal Server Error"}


def test_review_creates_result_transitions_attempt_and_returns_complete_result(client):
    teacher_id, token = auth(client, "review@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    attempt_id = add_submitted(definition_id)
    use(client, token)
    path = f"{item_path(space_id, activity_id, attempt_id)}/review"

    missing_origin = client.post(
        path,
        json={"score": 8, "max_score": 10},
    )
    assert missing_origin.status_code == 403

    invalid_score = client.post(
        path,
        json={"score": 11, "max_score": 10},
        headers=HEADERS,
    )
    assert invalid_score.status_code == 422
    assert stored_status(attempt_id) == "submitted"
    assert result_count() == 0

    response = client.post(
        path,
        json={"score": 8, "max_score": 10, "feedback": "   "},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": response.json()["id"],
        "attempt_id": str(attempt_id),
        "score": 8,
        "max_score": 10,
        "feedback": None,
    }
    assert stored_status(attempt_id) == "reviewed"
    assert stored_submission(attempt_id) == "Student answer"
    assert result_count() == 1

    repeated = client.post(
        path,
        json={"score": 9, "max_score": 10},
        headers=HEADERS,
    )
    assert repeated.status_code == 409
    assert stored_status(attempt_id) == "reviewed"
    assert stored_submission(attempt_id) == "Student answer"
    assert result_count() == 1


def test_correction_updates_single_result_and_keeps_attempt_reviewed(client):
    teacher_id, token = auth(client, "correct@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    attempt_id = add_reviewed(definition_id, score=4, feedback="Initial")
    use(client, token)
    path = f"{item_path(space_id, activity_id, attempt_id)}/correction"

    wrong_result = uuid4()
    missing = client.post(
        path,
        json={"result_id": str(wrong_result), "score": 9, "feedback": "x"},
        headers=HEADERS,
    )
    assert missing.status_code == 404
    assert stored_status(attempt_id) == "reviewed"
    assert result_count() == 1

    with TestingSession.begin() as db:
        result_id = str(
            SqlAlchemyAssessmentResultRepository(db).get_by_attempt(attempt_id).id  # type: ignore[union-attr]
        )

    corrected = client.post(
        path,
        json={"result_id": result_id, "score": 9, "feedback": "Updated"},
        headers=HEADERS,
    )
    assert corrected.status_code == 200
    assert corrected.json() == {
        "id": result_id,
        "attempt_id": str(attempt_id),
        "score": 9,
        "max_score": 10,
        "feedback": "Updated",
    }
    assert stored_status(attempt_id) == "reviewed"
    assert stored_submission(attempt_id) == "Student answer"
    assert result_count() == 1


def test_correction_requires_reviewed_attempt(client):
    teacher_id, token = auth(client, "correct-submitted@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    attempt_id = add_submitted(definition_id)
    use(client, token)
    response = client.post(
        f"{item_path(space_id, activity_id, attempt_id)}/correction",
        json={"result_id": str(uuid4()), "score": 9, "feedback": "x"},
        headers=HEADERS,
    )
    assert response.status_code == 409


def test_mutations_require_trusted_origin_but_reads_do_not(client):
    teacher_id, token = auth(client, "origin@example.com")
    space_id, activity_id, definition_id = teacher_space(teacher_id)
    attempt_id = add_submitted(definition_id)
    use(client, token)
    assert client.get(review_path(space_id, activity_id)).status_code == 200
    assert client.get(item_path(space_id, activity_id, attempt_id)).status_code == 200
    assert client.post(
        f"{item_path(space_id, activity_id, attempt_id)}/review",
        json={"score": 8, "max_score": 10},
    ).status_code == 403
