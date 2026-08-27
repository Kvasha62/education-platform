from collections.abc import Generator
from typing import Annotated, cast
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.application.attempts import AssessmentAttemptDetailService
from app.assessment.application.results import AssessmentResultService
from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure.attempts import SqlAlchemyAssessmentAttemptRepository
from app.assessment.infrastructure.models import AssessmentAttemptModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
from app.assessment.infrastructure.results import SqlAlchemyAssessmentResultRepository
from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.education.application.activity_publication import ActivityPublicationLookupService
from app.education.domain.models import (
    Activity,
    ActivityType,
    Course,
    EducationalEnvironment,
    LearningUnit,
    Section,
)
from app.education.infrastructure.activity_publication import (
    SqlAlchemyPublishedActivityRepository,
)
from app.education.infrastructure.repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyCourseRepository,
    SqlAlchemyEnvironmentRepository,
    SqlAlchemyLearningUnitRepository,
    SqlAlchemySectionRepository,
)
from app.identity.api.dependencies import SESSION_COOKIE_NAME
from app.learning.domain.models import Enrollment
from app.learning.infrastructure.models import EnrollmentModel
from app.learning.infrastructure.progress import SqlAlchemyEnrollmentVerifier
from app.learning.infrastructure.repositories import SqlAlchemyEnrollmentRepository
from app.main import app
from app.student_space.api.dependencies import get_student_assessment_attempt_service
from app.student_space.application.assessment_attempts import StudentAssessmentAttemptService

engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False, "autocommit": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
ORIGIN = "http://frontend.test"
HEADERS = {"Origin": ORIGIN}
MISSING_CREATE_PATH = (
    "/api/v1/student/activities/00000000-0000-0000-0000-000000000001/"
    "assessment-definitions/00000000-0000-0000-0000-000000000002/attempts"
)


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


class FailingAttemptDetailService:
    def from_attempt(self, attempt):
        raise RuntimeError("response assembly failed")


def failing_student_assessment_service(
    db: Annotated[Session, Depends(get_db)],
) -> StudentAssessmentAttemptService:
    service = get_student_assessment_attempt_service(db)
    service.attempt_details = cast(
        AssessmentAttemptDetailService,
        FailingAttemptDetailService(),
    )
    return service


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


def seed_scope(
    student_id: UUID,
    *,
    published: bool = True,
    enrolled: bool = True,
    archived_definition: bool = False,
) -> tuple[UUID, UUID, UUID]:
    with TestingSession.begin() as db:
        environment = SqlAlchemyEnvironmentRepository(db).add(
            EducationalEnvironment.create(uuid4(), "Environment")
        )
        course_repository = SqlAlchemyCourseRepository(db)
        course = course_repository.add(Course.create(environment.id, "Course"))
        if published:
            course = course_repository.update(course.publish())
        section = SqlAlchemySectionRepository(db).add(
            Section.create(course.id, "Section", 0)
        )
        unit = SqlAlchemyLearningUnitRepository(db).add(
            LearningUnit.create(section.id, "Unit", 0)
        )
        activity = SqlAlchemyActivityRepository(db).add(
            Activity.create(unit.id, "Assessment", ActivityType.HOMEWORK, 0)
        )
        definition_repository = SqlAlchemyAssessmentDefinitionRepository(db)
        definition = definition_repository.add(
            AssessmentDefinition.create(activity.id, "Answer in plain text")
        )
        if archived_definition:
            definition = definition_repository.update(definition.archive())
        if enrolled:
            SqlAlchemyEnrollmentRepository(db).get_or_create(
                Enrollment.create(student_id, course.id)
            )
    return activity.id, definition.id, course.id


def create_path(activity_id: UUID, definition_id: UUID) -> str:
    return (
        f"/api/v1/student/activities/{activity_id}"
        f"/assessment-definitions/{definition_id}/attempts"
    )


def attempt_path(attempt_id: str | UUID) -> str:
    return f"/api/v1/student/assessment-attempts/{attempt_id}"


def create_attempt(
    client: TestClient,
    activity_id: UUID,
    definition_id: UUID,
    submission=None,
):
    payload = {} if submission is ... else {"submission": submission}
    return client.post(
        create_path(activity_id, definition_id),
        json=payload,
        headers=HEADERS,
    )


def remove_enrollment(student_id: UUID, course_id: UUID) -> None:
    with TestingSession.begin() as db:
        db.execute(
            delete(EnrollmentModel).where(
                EnrollmentModel.student_user_id == student_id,
                EnrollmentModel.course_id == course_id,
            )
        )


def archive_course(course_id: UUID) -> None:
    with TestingSession.begin() as db:
        repository = SqlAlchemyCourseRepository(db)
        course = repository.get_by_id(course_id)
        assert course is not None
        repository.update(course.archive())


def review_attempt(
    attempt_id: UUID,
    definition_id: UUID,
    activity_id: UUID,
    *,
    score: int = 8,
    max_score: int = 10,
):
    with TestingSession.begin() as db:
        return AssessmentResultService(
            SqlAlchemyAssessmentResultRepository(db),
            SqlAlchemyAssessmentAttemptRepository(db),
            SqlAlchemyAssessmentDefinitionRepository(db),
        ).review(
            attempt_id,
            definition_id,
            activity_id,
            score,
            max_score,
            "Good work",
        )


def stored_attempt(attempt_id: UUID):
    with TestingSession() as db:
        return db.scalar(
            select(AssessmentAttemptModel).where(AssessmentAttemptModel.id == attempt_id)
        )


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        ("post", MISSING_CREATE_PATH, {}),
        (
            "put",
            "/api/v1/student/assessment-attempts/00000000-0000-0000-0000-000000000003",
            {"submission": None},
        ),
        (
            "post",
            "/api/v1/student/assessment-attempts/00000000-0000-0000-0000-000000000003/submit",
            None,
        ),
        (
            "get",
            "/api/v1/student/assessment-attempts/00000000-0000-0000-0000-000000000003",
            None,
        ),
    ],
)
def test_all_assessment_endpoints_require_authentication(client, method, path, json_body):
    response = client.request(method, path, json=json_body, headers=HEADERS)
    assert response.status_code == 401


def test_create_normalization_shape_identity_and_non_idempotency(client):
    student_id, _ = auth(client, "create@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)

    empty = create_attempt(client, activity_id, definition_id, ...)
    explicit_null = create_attempt(client, activity_id, definition_id, None)
    blank = create_attempt(client, activity_id, definition_id, "   ")
    meaningful = create_attempt(client, activity_id, definition_id, "  answer  ")

    for response in (empty, explicit_null, blank, meaningful):
        assert response.status_code == 201
        assert set(response.json()) == {
            "id",
            "assessment_definition_id",
            "submission",
            "status",
            "result",
        }
        assert response.json()["status"] == "draft"
        assert response.json()["result"] is None
        assert response.json()["assessment_definition_id"] == str(definition_id)
    assert empty.json()["submission"] is None
    assert explicit_null.json()["submission"] is None
    assert blank.json()["submission"] is None
    assert meaningful.json()["submission"] == "  answer  "
    assert len({response.json()["id"] for response in (empty, explicit_null, blank)}) == 3

    controlled_identity = client.post(
        create_path(activity_id, definition_id),
        json={"submission": "answer", "student_id": str(uuid4())},
        headers=HEADERS,
    )
    assert controlled_identity.status_code == 422
    assert create_attempt(client, activity_id, definition_id, 1).status_code == 422
    with TestingSession() as db:
        attempts = db.scalars(select(AssessmentAttemptModel)).all()
        assert attempts
        assert {attempt.student_id for attempt in attempts} == {student_id}


def test_create_scope_archival_and_current_access_errors(client):
    student_id, _ = auth(client, "create-errors@example.com")
    activity_a, definition_a, _ = seed_scope(student_id)
    activity_b, definition_b, _ = seed_scope(student_id)

    mismatch = create_attempt(client, activity_a, definition_b, None)
    assert mismatch.status_code == 404

    non_enrolled_activity, _, _ = seed_scope(student_id, enrolled=False)
    concealed_before_enrollment = create_attempt(
        client,
        non_enrolled_activity,
        definition_b,
        None,
    )
    assert concealed_before_enrollment.status_code == 404

    archived_activity, archived_definition, _ = seed_scope(
        student_id, archived_definition=True
    )
    archived = create_attempt(client, archived_activity, archived_definition, None)
    assert archived.status_code == 409

    hidden_activity, hidden_definition, _ = seed_scope(student_id, published=False)
    hidden = create_attempt(client, hidden_activity, hidden_definition, None)
    assert hidden.status_code == 404

    unenrolled_activity, unenrolled_definition, _ = seed_scope(
        student_id, enrolled=False
    )
    unenrolled = create_attempt(client, unenrolled_activity, unenrolled_definition, None)
    assert unenrolled.status_code == 403

    assert definition_a != definition_b
    assert activity_a != activity_b
    with TestingSession() as db:
        assert db.scalar(select(func.count()).select_from(AssessmentAttemptModel)) == 0


def test_replace_normalization_repeat_safety_and_required_field(client):
    student_id, _ = auth(client, "replace@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, None).json()
    path = attempt_path(created["id"])

    for value, expected in (
        ("answer", "answer"),
        ("replacement", "replacement"),
        (None, None),
        (None, None),
        ("", None),
        (" \t ", None),
    ):
        response = client.put(path, json={"submission": value}, headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["submission"] == expected
        assert response.json()["result"] is None

    assert client.put(path, json={}, headers=HEADERS).status_code == 422
    assert client.put(path, json={"submission": 1}, headers=HEADERS).status_code == 422


def test_replace_conceals_owner_and_rejects_current_access_and_immutable_states(client):
    owner_id, owner_token = auth(client, "replace-owner@example.com")
    activity_id, definition_id, course_id = seed_scope(owner_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    path = attempt_path(created["id"])

    auth(client, "replace-other@example.com")
    assert client.put(path, json={"submission": "x"}, headers=HEADERS).status_code == 404

    use(client, owner_token)
    archive_course(course_id)
    assert client.put(path, json={"submission": "x"}, headers=HEADERS).status_code == 403

    activity_id, definition_id, course_id = seed_scope(owner_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    remove_enrollment(owner_id, course_id)
    assert (
        client.put(
            attempt_path(created["id"]),
            json={"submission": "x"},
            headers=HEADERS,
        ).status_code
        == 403
    )

    activity_id, definition_id, _ = seed_scope(owner_id)
    submitted = create_attempt(client, activity_id, definition_id, "answer").json()
    submit_path = f"{attempt_path(submitted['id'])}/submit"
    assert client.post(submit_path, headers=HEADERS).status_code == 200
    assert (
        client.put(
            attempt_path(submitted["id"]),
            json={"submission": "x"},
            headers=HEADERS,
        ).status_code
        == 409
    )
    reviewed = review_attempt(
        UUID(submitted["id"]), definition_id, activity_id
    )
    assert reviewed.attempt_id == UUID(submitted["id"])
    assert client.put(
        attempt_path(submitted["id"]),
        json={"submission": "x"},
        headers=HEADERS,
    ).status_code == 409


@pytest.mark.parametrize("submission", ["", "   ", "\t\n"])
def test_submit_rejects_blank_and_whitespace_submission(client, submission):
    student_id, _ = auth(client, f"blank-{uuid4()}@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, submission).json()

    response = client.post(f"{attempt_path(created['id'])}/submit", headers=HEADERS)

    assert response.status_code == 422
    assert stored_attempt(UUID(created["id"])).status.value == "draft"


def test_submit_requires_current_publication_and_enrollment(client):
    student_id, _ = auth(client, "submit-access@example.com")
    activity_id, definition_id, course_id = seed_scope(student_id)
    hidden = create_attempt(client, activity_id, definition_id, "answer").json()
    archive_course(course_id)
    assert client.post(
        f"{attempt_path(hidden['id'])}/submit", headers=HEADERS
    ).status_code == 403

    activity_id, definition_id, course_id = seed_scope(student_id)
    unenrolled = create_attempt(client, activity_id, definition_id, "answer").json()
    remove_enrollment(student_id, course_id)
    assert client.post(
        f"{attempt_path(unenrolled['id'])}/submit", headers=HEADERS
    ).status_code == 403


def test_submit_validation_success_repetition_and_reviewed_conflict(client):
    student_id, _ = auth(client, "submit@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, None).json()
    submit_path = f"{attempt_path(created['id'])}/submit"

    empty = client.post(submit_path, headers=HEADERS)
    assert empty.status_code == 422
    assert stored_attempt(UUID(created["id"])).status.value == "draft"

    client.put(
        attempt_path(created["id"]),
        json={"submission": "answer"},
        headers=HEADERS,
    )
    submitted = client.post(submit_path, headers=HEADERS)
    assert submitted.status_code == 200
    assert submitted.json() == {
        "id": created["id"],
        "assessment_definition_id": str(definition_id),
        "submission": "answer",
        "status": "submitted",
        "result": None,
    }
    assert client.post(submit_path, headers=HEADERS).status_code == 409

    review_attempt(UUID(created["id"]), definition_id, activity_id)
    assert client.post(submit_path, headers=HEADERS).status_code == 409


def test_historical_detail_and_complete_reviewed_result_ignore_current_access(client):
    student_id, _ = auth(client, "history@example.com")
    activity_id, definition_id, course_id = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    path = attempt_path(created["id"])
    client.post(f"{path}/submit", headers=HEADERS)

    remove_enrollment(student_id, course_id)
    archive_course(course_id)
    submitted = client.get(path)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["result"] is None

    result = review_attempt(UUID(created["id"]), definition_id, activity_id)
    reviewed = client.get(path)
    assert reviewed.status_code == 200
    assert reviewed.json()["result"] == {
        "id": str(result.id),
        "attempt_id": created["id"],
        "score": 8,
        "max_score": 10,
        "feedback": "Good work",
    }


def test_detail_conceals_foreign_attempt_and_requires_current_access_for_draft(client):
    owner_id, owner_token = auth(client, "detail-owner@example.com")
    activity_id, definition_id, course_id = seed_scope(owner_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    path = attempt_path(created["id"])

    _, other_token = auth(client, "detail-other@example.com")
    assert client.get(path).status_code == 404
    assert client.get(attempt_path(uuid4())).status_code == 404

    use(client, owner_token)
    archive_course(course_id)
    assert client.get(path).status_code == 403
    use(client, other_token)


def test_detail_conceals_invalid_assessment_scope_binding(client):
    student_id, _ = auth(client, "invalid-scope@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    attempt_id = UUID(created["id"])
    with TestingSession.begin() as db:
        attempt = db.get(AssessmentAttemptModel, attempt_id)
        assert attempt is not None
        attempt.assessment_definition_id = uuid4()

    assert client.get(attempt_path(attempt_id)).status_code == 404


def test_reviewed_without_result_returns_500_without_partial_aggregate(client):
    student_id, _ = auth(client, "invariant@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    created = create_attempt(client, activity_id, definition_id, "answer").json()
    attempt_id = UUID(created["id"])
    with TestingSession.begin() as db:
        repository = SqlAlchemyAssessmentAttemptRepository(db)
        attempt = repository.get_owned_by_id(attempt_id, student_id)
        assert attempt is not None
        repository.update(attempt.submit().review())

    response = client.get(attempt_path(attempt_id))
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "submission" not in response.json()


def test_mutations_require_trusted_origin_but_detail_does_not(client):
    student_id, _ = auth(client, "origin@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    create = create_path(activity_id, definition_id)
    assert client.post(create, json={}).status_code == 403

    created = client.post(create, json={}, headers=HEADERS).json()
    path = attempt_path(created["id"])
    assert client.put(path, json={"submission": "answer"}).status_code == 403
    assert client.post(f"{path}/submit").status_code == 403
    assert client.get(path).status_code == 200


def test_request_transaction_rolls_back_unexpected_create_failure(client):
    student_id, token = auth(client, "rollback@example.com")
    activity_id, definition_id, _ = seed_scope(student_id)
    app.dependency_overrides[
        get_student_assessment_attempt_service
    ] = failing_student_assessment_service
    try:
        with TestClient(app, raise_server_exceptions=False) as failing_client:
            failing_client.cookies.set(SESSION_COOKIE_NAME, token)
            response = failing_client.post(
                create_path(activity_id, definition_id),
                json={"submission": "answer"},
                headers=HEADERS,
            )
    finally:
        app.dependency_overrides.pop(get_student_assessment_attempt_service, None)

    assert response.status_code == 500
    with TestingSession() as db:
        assert db.scalar(
            select(AssessmentAttemptModel).where(
                AssessmentAttemptModel.student_id == student_id,
                AssessmentAttemptModel.assessment_definition_id == definition_id,
            )
        ) is None


def test_production_composition_uses_one_request_scoped_session():
    with TestingSession() as db:
        service = get_student_assessment_attempt_service(db)
        activity_lookup = cast(ActivityPublicationLookupService, service.activities)
        activity_repository = cast(
            SqlAlchemyPublishedActivityRepository, activity_lookup.activities
        )
        enrollment_verifier = cast(SqlAlchemyEnrollmentVerifier, service.enrollments)
        mutation_attempts = cast(
            SqlAlchemyAssessmentAttemptRepository, service.attempts.attempts
        )
        mutation_definitions = cast(
            SqlAlchemyAssessmentDefinitionRepository, service.attempts.definitions
        )
        detail_attempts = cast(
            SqlAlchemyAssessmentAttemptRepository,
            service.attempt_details.attempts.attempts,
        )
        detail_definitions = cast(
            SqlAlchemyAssessmentDefinitionRepository,
            service.attempt_details.attempts.definitions,
        )
        detail_results = cast(
            SqlAlchemyAssessmentResultRepository, service.attempt_details.results
        )

        assert activity_repository.db is db
        assert enrollment_verifier.db is db
        assert mutation_attempts.db is db
        assert mutation_definitions.db is db
        assert detail_attempts.db is db
        assert detail_definitions.db is db
        assert detail_results.db is db


def test_openapi_contains_exact_assessment_contract(client):
    openapi = client.get("/openapi.json").json()
    assessment_paths = {
        path: methods
        for path, methods in openapi["paths"].items()
        if "assessment" in path
    }
    assert set(assessment_paths) == {
        "/api/v1/student/activities/{activity_id}/assessment-definitions/{definition_id}/attempts",
        "/api/v1/student/assessment-attempts/{attempt_id}",
        "/api/v1/student/assessment-attempts/{attempt_id}/submit",
    }
    assert set(
        assessment_paths[
            "/api/v1/student/activities/{activity_id}/assessment-definitions/"
            "{definition_id}/attempts"
        ]
    ) == {"post"}
    assert set(
        assessment_paths["/api/v1/student/assessment-attempts/{attempt_id}"]
    ) == {"get", "put"}
    assert set(
        assessment_paths["/api/v1/student/assessment-attempts/{attempt_id}/submit"]
    ) == {"post"}

    schemas = openapi["components"]["schemas"]
    assert set(schemas["AssessmentAttemptResponse"]["properties"]) == {
        "id",
        "assessment_definition_id",
        "submission",
        "status",
        "result",
    }
    assert set(schemas["AssessmentResultResponse"]["properties"]) == {
        "id",
        "attempt_id",
        "score",
        "max_score",
        "feedback",
    }
    create_operation = assessment_paths[
        "/api/v1/student/activities/{activity_id}/assessment-definitions/"
        "{definition_id}/attempts"
    ]["post"]
    replace_operation = assessment_paths[
        "/api/v1/student/assessment-attempts/{attempt_id}"
    ]["put"]
    submit_operation = assessment_paths[
        "/api/v1/student/assessment-attempts/{attempt_id}/submit"
    ]["post"]
    detail_operation = assessment_paths[
        "/api/v1/student/assessment-attempts/{attempt_id}"
    ]["get"]
    assert set(create_operation["responses"]) >= {"201", "401", "403", "404", "409", "422", "500"}
    for operation in (replace_operation, submit_operation):
        assert set(operation["responses"]) >= {
            "200",
            "401",
            "403",
            "404",
            "409",
            "422",
            "500",
        }
    assert set(detail_operation["responses"]) >= {
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
    }
    assert "409" not in detail_operation["responses"]

    assert "submission" not in schemas["CreateAssessmentAttemptRequest"].get("required", [])
    assert schemas["ReplaceAssessmentAttemptRequest"]["required"] == ["submission"]
    assert "requestBody" not in submit_operation
    assert "student_id" not in str(assessment_paths)
    assert "student_id" not in str(schemas["CreateAssessmentAttemptRequest"])
    assert "student_id" not in str(schemas["ReplaceAssessmentAttemptRequest"])
