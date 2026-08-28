from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.domain.models import AssessmentDefinition
from app.assessment.infrastructure.models import AssessmentDefinitionModel
from app.assessment.infrastructure.repositories import SqlAlchemyAssessmentDefinitionRepository
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


def seed_scope(
    owner_id: UUID,
    *,
    create_definition: bool = True,
    definition_status: str = "active",
) -> tuple[UUID, UUID, UUID | None]:
    with TestingSession.begin() as db:
        space = SqlAlchemyTeacherSpaceRepository(db).add(
            TeacherSpace.create(owner_id, "Teacher Space")
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
            Activity.create(unit.id, "Assessment", ActivityType.HOMEWORK, 0)
        )
        definition_id = None
        if create_definition:
            repository = SqlAlchemyAssessmentDefinitionRepository(db)
            definition = repository.add(
                AssessmentDefinition.create(activity.id, "Initial instructions")
            )
            if definition_status == "archived":
                definition = repository.update(definition.archive())
            definition_id = definition.id
    return space.id, activity.id, definition_id


def definition_path(space_id: UUID, activity_id: UUID) -> str:
    return (
        f"/api/v1/teacher-spaces/{space_id}/activities/{activity_id}"
        "/assessment-definition"
    )


def archive_path(space_id: UUID, activity_id: UUID) -> str:
    return f"{definition_path(space_id, activity_id)}/archive"


def stored_definition(
    activity_id: UUID,
) -> tuple[str | None, str]:
    with TestingSession() as db:
        model = db.scalar(
            select(AssessmentDefinitionModel).where(
                AssessmentDefinitionModel.activity_id == activity_id
            )
        )
        assert model is not None
        return model.instructions, model.status.value


def definition_count() -> int:
    with TestingSession() as db:
        value = db.scalar(select(func.count()).select_from(AssessmentDefinitionModel))
        assert value is not None
        return value


def test_all_definition_endpoints_require_authentication(client):
    space_id, activity_id, _ = seed_scope(uuid4())
    for path in (
        definition_path(space_id, activity_id),
        definition_path(space_id, activity_id),
    ):
        assert client.get(path, headers=HEADERS).status_code == 401
    for path, payload in (
        (definition_path(space_id, activity_id), {"instructions": "x"}),
        (definition_path(space_id, activity_id), {"instructions": "x"}),
        (archive_path(space_id, activity_id), {}),
    ):
        assert client.post(path, json=payload, headers=HEADERS).status_code == 401
    assert (
        client.patch(
            definition_path(space_id, activity_id),
            json={"instructions": "x"},
            headers=HEADERS,
        ).status_code
        == 401
    )


def test_get_existing_active_definition(client):
    owner, token = auth(client, "get-active@example.com")
    space_id, activity_id, definition_id = seed_scope(owner)
    use(client, token)

    response = client.get(definition_path(space_id, activity_id), headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "id": str(definition_id),
        "activity_id": str(activity_id),
        "instructions": "Initial instructions",
        "status": "active",
    }


def test_get_existing_archived_definition(client):
    owner, token = auth(client, "get-archived@example.com")
    space_id, activity_id, definition_id = seed_scope(owner, definition_status="archived")
    use(client, token)

    response = client.get(definition_path(space_id, activity_id), headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "id": str(definition_id),
        "activity_id": str(activity_id),
        "instructions": "Initial instructions",
        "status": "archived",
    }


def test_get_missing_definition_returns_404(client):
    owner, token = auth(client, "get-missing-definition@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.get(definition_path(space_id, activity_id), headers=HEADERS)
    assert response.status_code == 404
    assert response.json() == {"detail": "Assessment Definition not found"}


def test_get_missing_activity_returns_404(client):
    owner, token = auth(client, "get-missing-activity@example.com")
    space_id, _, _ = seed_scope(owner)
    use(client, token)

    response = client.get(
        definition_path(space_id, uuid4()),
        headers=HEADERS,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_get_activity_outside_teacher_space_returns_403(client):
    owner, token = auth(client, "outside@example.com")
    _, _, _ = seed_scope(owner)
    other = uuid4()
    other_space_id, other_activity_id, _ = seed_scope(other)
    use(client, token)

    response = client.get(
        definition_path(other_space_id, other_activity_id),
        headers=HEADERS,
    )
    assert response.status_code == 403


def test_get_missing_teacher_space_returns_404(client):
    owner, token = auth(client, "missing-space@example.com")
    _, _, _ = seed_scope(owner)
    use(client, token)

    response = client.get(
        definition_path(uuid4(), uuid4()),
        headers=HEADERS,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Teacher Space not found"}


def test_other_teacher_cannot_get_definition(client):
    owner, _ = auth(client, "other-owner-get@example.com")
    space_id, activity_id, _ = seed_scope(owner)
    _, other_token = auth(client, "other-get@example.com")
    use(client, other_token)

    response = client.get(definition_path(space_id, activity_id), headers=HEADERS)
    assert response.status_code == 403


def test_create_definition_with_null_instructions(client):
    owner, token = auth(client, "create-null@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": None},
        headers=HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["activity_id"] == str(activity_id)
    assert body["instructions"] is None
    assert body["status"] == "active"
    assert body["id"]
    stored_instructions, stored_status = stored_definition(activity_id)
    assert stored_instructions is None
    assert stored_status == "active"


def test_create_definition_with_instructions(client):
    owner, token = auth(client, "create-text@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": "Write your answer."},
        headers=HEADERS,
    )
    assert response.status_code == 201
    assert response.json()["instructions"] == "Write your answer."
    assert response.json()["status"] == "active"
    assert stored_definition(activity_id) == ("Write your answer.", "active")


def test_create_definition_with_empty_instructions(client):
    owner, token = auth(client, "create-empty@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": ""},
        headers=HEADERS,
    )
    assert response.status_code == 201
    assert response.json()["instructions"] == ""
    assert response.json()["status"] == "active"
    assert stored_definition(activity_id) == ("", "active")


def test_duplicate_create_returns_409_and_leaves_original(client):
    owner, token = auth(client, "duplicate-create@example.com")
    space_id, activity_id, _ = seed_scope(owner)
    use(client, token)

    response = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": "Second"},
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Assessment Definition already exists"}
    assert definition_count() == 1
    assert stored_definition(activity_id) == ("Initial instructions", "active")


def test_create_for_activity_outside_teacher_scope_forbidden(client):
    owner, token = auth(client, "create-outside@example.com")
    _, _, _ = seed_scope(owner)
    other_space_id, other_activity_id, _ = seed_scope(uuid4())
    use(client, token)

    response = client.post(
        definition_path(other_space_id, other_activity_id),
        json={"instructions": "x"},
        headers=HEADERS,
    )
    assert response.status_code == 403


def test_create_rejects_activity_id_and_unknown_fields(client):
    owner, token = auth(client, "create-extra@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    with_activity_id = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": "x", "activity_id": str(activity_id)},
        headers=HEADERS,
    )
    assert with_activity_id.status_code == 422

    unknown = client.post(
        definition_path(space_id, activity_id),
        json={"instructions": "x", "title": "not allowed"},
        headers=HEADERS,
    )
    assert unknown.status_code == 422
    assert definition_count() == 0


def test_create_requires_instructions_field(client):
    owner, token = auth(client, "create-missing-instructions@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.post(
        definition_path(space_id, activity_id),
        json={},
        headers=HEADERS,
    )
    assert response.status_code == 422
    assert definition_count() == 0


def test_patch_updates_instructions(client):
    owner, token = auth(client, "patch-update@example.com")
    space_id, activity_id, _ = seed_scope(owner)
    use(client, token)

    response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": "Updated"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["instructions"] == "Updated"
    assert response.json()["status"] == "active"
    assert stored_definition(activity_id) == ("Updated", "active")


def test_patch_can_set_null_and_empty_instructions(client):
    owner, token = auth(client, "patch-null-empty@example.com")
    space_id, activity_id, _ = seed_scope(owner)
    use(client, token)

    null_response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": None},
        headers=HEADERS,
    )
    assert null_response.status_code == 200
    assert null_response.json()["instructions"] is None
    assert stored_definition(activity_id) == (None, "active")

    empty_response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": ""},
        headers=HEADERS,
    )
    assert empty_response.status_code == 200
    assert empty_response.json()["instructions"] == ""
    assert stored_definition(activity_id) == ("", "active")


def test_patch_archived_definition_returns_409_and_keeps_state(client):
    owner, token = auth(client, "patch-archived@example.com")
    space_id, activity_id, _ = seed_scope(owner, definition_status="archived")
    use(client, token)

    response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": "changed"},
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Assessment Definition is archived"}
    assert stored_definition(activity_id) == ("Initial instructions", "archived")


def test_patch_rejects_id_activity_id_and_status(client):
    owner, token = auth(client, "patch-immutable@example.com")
    space_id, activity_id, definition_id = seed_scope(owner)
    use(client, token)

    for payload in (
        {"instructions": "x", "id": str(definition_id)},
        {"instructions": "x", "activity_id": str(activity_id)},
        {"instructions": "x", "status": "archived"},
    ):
        response = client.patch(
            definition_path(space_id, activity_id),
            json=payload,
            headers=HEADERS,
        )
        assert response.status_code == 422
    assert stored_definition(activity_id) == ("Initial instructions", "active")


def test_patch_missing_definition_returns_404(client):
    owner, token = auth(client, "patch-missing@example.com")
    space_id, activity_id, _ = seed_scope(owner, create_definition=False)
    use(client, token)

    response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": "x"},
        headers=HEADERS,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Assessment Definition not found"}


def test_patch_outside_teacher_scope_forbidden(client):
    owner, token = auth(client, "patch-outside@example.com")
    _, _, _ = seed_scope(owner)
    other_space_id, other_activity_id, _ = seed_scope(uuid4())
    use(client, token)

    response = client.patch(
        definition_path(other_space_id, other_activity_id),
        json={"instructions": "x"},
        headers=HEADERS,
    )
    assert response.status_code == 403


def test_archive_active_definition(client):
    owner, token = auth(client, "archive-active@example.com")
    space_id, activity_id, definition_id = seed_scope(owner)
    use(client, token)

    response = client.post(archive_path(space_id, activity_id), json={}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == str(definition_id)
    assert response.json()["status"] == "archived"
    assert stored_definition(activity_id) == ("Initial instructions", "archived")


def test_repeat_archive_returns_409_and_keeps_archived(client):
    owner, token = auth(client, "archive-repeat@example.com")
    space_id, activity_id, _ = seed_scope(owner, definition_status="archived")
    use(client, token)

    first = client.post(archive_path(space_id, activity_id), json={}, headers=HEADERS)
    assert first.status_code == 409
    assert first.json() == {
        "detail": "Assessment Definition is already archived"
    }
    assert stored_definition(activity_id) == ("Initial instructions", "archived")


def test_cannot_restore_archived_definition_via_patch(client):
    owner, token = auth(client, "no-restore@example.com")
    space_id, activity_id, _ = seed_scope(owner, definition_status="archived")
    use(client, token)

    response = client.patch(
        definition_path(space_id, activity_id),
        json={"instructions": "x", "status": "active"},
        headers=HEADERS,
    )
    assert response.status_code in {409, 422}
    assert stored_definition(activity_id) == ("Initial instructions", "archived")


def test_mutations_require_trusted_origin_but_reads_do_not(client):
    owner, token = auth(client, "origin-definition@example.com")
    space_id, activity_id, _ = seed_scope(owner)
    use(client, token)

    assert (
        client.get(definition_path(space_id, activity_id)).status_code == 200
    )
    assert (
        client.post(
            definition_path(space_id, activity_id),
            json={"instructions": "x"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            definition_path(space_id, activity_id),
            json={"instructions": "x"},
        ).status_code
        == 403
    )
    assert (
        client.post(archive_path(space_id, activity_id), json={}).status_code == 403
    )
