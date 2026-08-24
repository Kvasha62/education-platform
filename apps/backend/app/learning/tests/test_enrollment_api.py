from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.identity.api.dependencies import SESSION_COOKIE_NAME
from app.learning.infrastructure.models import EnrollmentModel
from app.main import app

engine = create_engine(
    "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
Factory = sessionmaker(bind=engine, expire_on_commit=False)
ORIGIN = "http://frontend.test"
HEADERS = {"Origin": ORIGIN}


def override_db() -> Generator[Session, None, None]:
    with Factory() as session:
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


def auth(client: TestClient, email: str) -> str:
    client.cookies.clear()
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a secure password"},
    ).status_code == 201
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a secure password"},
    ).status_code == 200
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return token


def create_course(client: TestClient, title: str) -> tuple[str, str]:
    space = client.post(
        "/api/v1/teacher-spaces", json={"name": title}, headers=HEADERS
    ).json()
    environment = f"/api/v1/teacher-spaces/{space['id']}/environment"
    client.post(environment, json={"name": title}, headers=HEADERS)
    course = client.post(
        f"{environment}/courses", json={"title": title}, headers=HEADERS
    ).json()
    path = f"/api/v1/teacher-spaces/{space['id']}/environment/courses/{course['id']}"
    return path, course["id"]


def enrollment_path(course_id: str) -> str:
    return f"/api/v1/student/courses/{course_id}/enrollment"


def test_authentication_and_course_visibility(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(enrollment_path(missing), headers=HEADERS).status_code == 401

    teacher = auth(client, "teacher@example.com")
    _draft_path, draft_id = create_course(client, "Draft")
    student = auth(client, "student@example.com")
    assert client.post(enrollment_path(draft_id), headers=HEADERS).status_code == 404
    assert client.post(enrollment_path(missing), headers=HEADERS).status_code == 404

    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    published_path, published_id = create_course(client, "Published")
    assert client.post(f"{published_path}/publish", headers=HEADERS).status_code == 200
    archived_path, archived_id = create_course(client, "Archived")
    client.post(f"{archived_path}/publish", headers=HEADERS)
    client.post(f"{archived_path}/archive", headers=HEADERS)

    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.post(enrollment_path(published_id), headers=HEADERS).status_code == 201
    assert client.post(enrollment_path(archived_id), headers=HEADERS).status_code == 404


def test_enrollment_is_idempotent_and_isolated_by_user(client: TestClient) -> None:
    teacher = auth(client, "teacher@example.com")
    course_path, course_id = create_course(client, "Published")
    client.post(f"{course_path}/publish", headers=HEADERS)

    first_user = auth(client, "first@example.com")
    first = client.post(enrollment_path(course_id), headers=HEADERS)
    repeated = client.post(enrollment_path(course_id), headers=HEADERS)
    assert first.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["course_id"] == first.json()["course_id"]
    assert repeated.json()["status"] == first.json()["status"]
    assert set(first.json()) == {"id", "course_id", "status", "created_at"}
    assert first.json()["status"] == "enrolled"

    second_user = auth(client, "second@example.com")
    second = client.post(enrollment_path(course_id), headers=HEADERS)
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]

    with Factory() as session:
        assert session.scalar(select(func.count()).select_from(EnrollmentModel)) == 2
        rows = session.scalars(select(EnrollmentModel)).all()
        assert len({(row.student_user_id, row.course_id) for row in rows}) == 2

    client.cookies.set(SESSION_COOKIE_NAME, first_user)
    assert client.post(enrollment_path(course_id), headers=HEADERS).json()["id"] == first.json()["id"]
    client.cookies.set(SESSION_COOKIE_NAME, second_user)
    assert client.post(enrollment_path(course_id), headers=HEADERS).json()["id"] == second.json()["id"]
    client.cookies.set(SESSION_COOKIE_NAME, teacher)


def test_openapi_contains_exact_enrollment_contract(client: TestClient) -> None:
    path = "/api/v1/student/courses/{course_id}/enrollment"
    operation = client.get("/openapi.json").json()["paths"][path]["post"]
    assert operation["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EnrollmentResponse"
    }


def test_student_lists_only_own_enrollments_and_empty_list(client: TestClient) -> None:
    missing_auth = client.get("/api/v1/student/enrollments")
    assert missing_auth.status_code == 401

    teacher = auth(client, "teacher-list@example.com")
    first_path, first_id = create_course(client, "First")
    second_path, second_id = create_course(client, "Second")
    client.post(f"{first_path}/publish", headers=HEADERS)
    client.post(f"{second_path}/publish", headers=HEADERS)

    first_student = auth(client, "first-list@example.com")
    assert client.get("/api/v1/student/enrollments").json() == {"items": []}
    client.post(enrollment_path(first_id), headers=HEADERS)
    client.post(enrollment_path(second_id), headers=HEADERS)
    own = client.get("/api/v1/student/enrollments")
    assert own.status_code == 200
    assert [item["course_id"] for item in own.json()["items"]] == [first_id, second_id]
    assert all(
        set(item) == {"id", "course_id", "status", "created_at"}
        for item in own.json()["items"]
    )

    second_student = auth(client, "second-list@example.com")
    assert client.get("/api/v1/student/enrollments").json() == {"items": []}
    client.post(enrollment_path(second_id), headers=HEADERS)
    second_own = client.get("/api/v1/student/enrollments").json()["items"]
    assert len(second_own) == 1
    assert second_own[0]["course_id"] == second_id

    client.cookies.set(SESSION_COOKIE_NAME, first_student)
    assert len(client.get("/api/v1/student/enrollments").json()["items"]) == 2
    client.cookies.set(SESSION_COOKIE_NAME, second_student)
    assert len(client.get("/api/v1/student/enrollments").json()["items"]) == 1
    client.cookies.set(SESSION_COOKIE_NAME, teacher)


def test_openapi_contains_enrollment_list_contract(client: TestClient) -> None:
    path = "/api/v1/student/enrollments"
    operation = client.get("/openapi.json").json()["paths"][path]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StudentEnrollmentListResponse"
    }
