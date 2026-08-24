from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.identity.api.dependencies import SESSION_COOKIE_NAME
from app.main import app

engine = create_engine(
    "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
TEST_ORIGIN = "http://frontend.test"
MUTATION_HEADERS = {"Origin": TEST_ORIGIN}


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def override_settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite://",
        minio_endpoint="http://minio.test",
        frontend_origin=TEST_ORIGIN,
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
    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def authenticate(client: TestClient, email: str) -> str:
    assert client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a secure password"}
    ).status_code == 201
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a secure password"}
    ).status_code == 200
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return token


def use_session(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)


def create_teacher_space(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/v1/teacher-spaces", json={"name": name}, headers=MUTATION_HEADERS
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_environment(client: TestClient, teacher_space_id: str) -> str:
    response = client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/environment",
        json={"name": "Environment"},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 201
    return response.json()["id"]


def courses_path(teacher_space_id: str) -> str:
    return f"/api/v1/teacher-spaces/{teacher_space_id}/environment/courses"


def create_course(client: TestClient, teacher_space_id: str, title: str):
    return client.post(
        courses_path(teacher_space_id),
        json={"title": title},
        headers=MUTATION_HEADERS,
    )


@pytest.mark.parametrize("method", ["post", "get", "patch"])
def test_course_endpoints_require_authentication(client: TestClient, method: str) -> None:
    base = courses_path("00000000-0000-0000-0000-000000000000")
    path = base if method != "patch" else f"{base}/00000000-0000-0000-0000-000000000000"
    response = client.request(
        method,
        path,
        json={"title": "Course"} if method != "get" else None,
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 401


def test_owner_can_create_list_get_and_update_multiple_courses(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Owner Space")
    environment_id = create_environment(client, teacher_space_id)

    first = create_course(client, teacher_space_id, "First")
    second = create_course(client, teacher_space_id, "Second")
    assert first.status_code == second.status_code == 201
    assert first.json()["educational_environment_id"] == environment_id
    assert first.json()["status"] == second.json()["status"] == "draft"

    listed = client.get(courses_path(teacher_space_id))
    assert [course["title"] for course in listed.json()] == ["First", "Second"]

    course_path = f"{courses_path(teacher_space_id)}/{first.json()['id']}"
    assert client.get(course_path).json()["title"] == "First"
    updated = client.patch(
        course_path, json={"title": "Updated"}, headers=MUTATION_HEADERS
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated"
    assert updated.json()["educational_environment_id"] == environment_id


def test_existing_empty_environment_returns_empty_course_list(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Empty Space")
    create_environment(client, teacher_space_id)

    response = client.get(courses_path(teacher_space_id))
    assert response.status_code == 200
    assert response.json() == []


def test_missing_course_get_returns_404(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)

    response = client.get(
        f"{courses_path(teacher_space_id)}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_missing_course_patch_returns_404(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)

    response = client.patch(
        f"{courses_path(teacher_space_id)}/00000000-0000-0000-0000-000000000000",
        json={"title": "Missing"},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 404


def test_create_course_without_environment_returns_404(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "No Environment")

    response = create_course(client, teacher_space_id, "Missing Environment")
    assert response.status_code == 404


def test_owner_publish_archive_and_idempotency(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    course = create_course(client, teacher_space_id, "Lifecycle").json()
    base = f"{courses_path(teacher_space_id)}/{course['id']}"

    published = client.post(f"{base}/publish", headers=MUTATION_HEADERS)
    published_again = client.post(f"{base}/publish", headers=MUTATION_HEADERS)
    assert published.status_code == published_again.status_code == 200
    assert published.json()["status"] == published_again.json()["status"] == "published"
    assert published.json()["updated_at"].removesuffix("Z") == published_again.json()[
        "updated_at"
    ].removesuffix("Z")

    archived = client.post(f"{base}/archive", headers=MUTATION_HEADERS)
    archived_again = client.post(f"{base}/archive", headers=MUTATION_HEADERS)
    assert archived.status_code == archived_again.status_code == 200
    assert archived.json()["status"] == archived_again.json()["status"] == "archived"


def test_invalid_lifecycle_transitions_return_conflict(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    course = create_course(client, teacher_space_id, "Lifecycle").json()
    base = f"{courses_path(teacher_space_id)}/{course['id']}"

    assert client.post(f"{base}/archive", headers=MUTATION_HEADERS).status_code == 409
    assert client.post(f"{base}/publish", headers=MUTATION_HEADERS).status_code == 200
    assert client.post(f"{base}/archive", headers=MUTATION_HEADERS).status_code == 200
    assert client.post(f"{base}/publish", headers=MUTATION_HEADERS).status_code == 409


def test_lifecycle_requires_authentication_and_csrf(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    base = f"{courses_path(missing)}/{missing}"
    assert client.post(f"{base}/publish", headers=MUTATION_HEADERS).status_code == 401
    assert client.post(f"{base}/archive", headers=MUTATION_HEADERS).status_code == 401

    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    course = create_course(client, teacher_space_id, "Lifecycle").json()
    base = f"{courses_path(teacher_space_id)}/{course['id']}"
    evil = {"Origin": "https://evil.test"}
    assert client.post(f"{base}/publish", headers=evil).status_code == 403
    assert client.post(f"{base}/archive", headers=evil).status_code == 403
    assert client.post(
        f"{courses_path(teacher_space_id)}/bad/publish", headers=MUTATION_HEADERS
    ).status_code == 422
    assert client.post(
        f"{courses_path(teacher_space_id)}/bad/archive", headers=MUTATION_HEADERS
    ).status_code == 422


def test_non_owner_cannot_access_courses(client: TestClient) -> None:
    owner_token = authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Owner Space")
    create_environment(client, teacher_space_id)
    course = create_course(client, teacher_space_id, "Private").json()

    authenticate(client, "other@example.com")
    base = courses_path(teacher_space_id)
    assert client.get(base).status_code == 404
    assert client.get(f"{base}/{course['id']}").status_code == 404
    assert create_course(client, teacher_space_id, "Stolen").status_code == 404
    assert client.patch(
        f"{base}/{course['id']}", json={"title": "Stolen"}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert client.post(f"{base}/{course['id']}/publish", headers=MUTATION_HEADERS).status_code == 404
    assert client.post(f"{base}/{course['id']}/archive", headers=MUTATION_HEADERS).status_code == 404
    use_session(client, owner_token)


def test_course_cannot_be_accessed_through_another_owned_environment(
    client: TestClient,
) -> None:
    authenticate(client, "owner@example.com")
    first_space = create_teacher_space(client, "First Space")
    create_environment(client, first_space)
    course = create_course(client, first_space, "First Course").json()

    second_space = create_teacher_space(client, "Second Space")
    create_environment(client, second_space)
    wrong_path = f"{courses_path(second_space)}/{course['id']}"
    assert client.get(wrong_path).status_code == 404
    assert client.patch(
        wrong_path, json={"title": "Moved"}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert client.post(f"{wrong_path}/publish", headers=MUTATION_HEADERS).status_code == 404
    assert client.post(f"{wrong_path}/archive", headers=MUTATION_HEADERS).status_code == 404


def test_client_cannot_control_environment_or_ownership(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    base = courses_path(teacher_space_id)
    assert client.post(
        base,
        json={"title": "Course", "owner_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    assert client.post(
        base, json={"title": "Course", "status": "published"}, headers=MUTATION_HEADERS
    ).status_code == 422
    assert client.post(
        base,
        json={
            "title": "Course",
            "educational_environment_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=MUTATION_HEADERS,
    ).status_code == 422
    course = create_course(client, teacher_space_id, "Course").json()
    assert client.patch(
        f"{base}/{course['id']}",
        json={"title": "Changed", "educational_environment_id": str(course["id"])},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    assert client.patch(
        f"{base}/{course['id']}",
        json={"title": "Changed", "status": "published"},
        headers=MUTATION_HEADERS,
    ).status_code == 422


def test_invalid_title_is_rejected(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    assert create_course(client, teacher_space_id, "   ").status_code == 422
    assert create_course(client, teacher_space_id, "x" * 121).status_code == 422


def test_disabled_teacher_space_courses_are_read_only(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "Space")
    create_environment(client, teacher_space_id)
    course = create_course(client, teacher_space_id, "Readable").json()
    assert client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/disable",
        headers=MUTATION_HEADERS,
    ).status_code == 200

    base = courses_path(teacher_space_id)
    assert client.get(base).status_code == 200
    assert client.get(f"{base}/{course['id']}").status_code == 200
    assert create_course(client, teacher_space_id, "Forbidden").status_code == 409
    assert client.patch(
        f"{base}/{course['id']}",
        json={"title": "Forbidden"},
        headers=MUTATION_HEADERS,
    ).status_code == 409
    assert client.post(f"{base}/{course['id']}/publish", headers=MUTATION_HEADERS).status_code == 409
    assert client.post(f"{base}/{course['id']}/archive", headers=MUTATION_HEADERS).status_code == 409


def test_openapi_contains_course_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    collection = "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses"
    item = f"{collection}/{{course_id}}"
    assert {"post", "get"} <= paths[collection].keys()
    assert {"get", "patch"} <= paths[item].keys()
    assert "post" in paths[f"{item}/publish"]
    assert "post" in paths[f"{item}/archive"]
    course_schema = client.get("/openapi.json").json()["components"]["schemas"]["CourseResponse"]
    assert "status" in course_schema["properties"]
    assert "delete" not in paths[item]
