from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.identity.api.dependencies import SESSION_COOKIE_NAME
from app.identity.api.rate_limit import login_limiter, register_limiter
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
    login_limiter.reset()
    register_limiter.reset()
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
    create_activity(client, published_path)
    assert client.post(f"{published_path}/publish", headers=HEADERS).status_code == 200
    archived_path, archived_id = create_course(client, "Archived")
    create_activity(client, archived_path)
    client.post(f"{archived_path}/publish", headers=HEADERS)
    client.post(f"{archived_path}/archive", headers=HEADERS)

    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.post(enrollment_path(published_id), headers=HEADERS).status_code == 201
    assert client.post(enrollment_path(archived_id), headers=HEADERS).status_code == 404


def test_enrollment_is_idempotent_and_isolated_by_user(client: TestClient) -> None:
    teacher = auth(client, "teacher@example.com")
    course_path, course_id = create_course(client, "Published")
    create_activity(client, course_path)
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
    create_activity(client, first_path)
    create_activity(client, second_path)
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


def create_activity(client: TestClient, course_path: str) -> str:
    sections = f"{course_path}/sections"
    section = client.post(
        sections, json={"title": "Section", "position": 0}, headers=HEADERS
    ).json()
    units = f"{sections}/{section['id']}/units"
    unit = client.post(units, json={"title": "Unit", "position": 0}, headers=HEADERS).json()
    activity = client.post(
        f"{units}/{unit['id']}/activities",
        json={"title": "Activity", "type": "lecture", "position": 0},
        headers=HEADERS,
    ).json()
    return activity["id"]


def test_activity_progress_lifecycle_access_and_isolation(client: TestClient) -> None:
    teacher = auth(client, "progress-teacher@example.com")
    course_path, course_id = create_course(client, "Progress")
    activity_id = create_activity(client, course_path)
    base = f"/api/v1/student/activities/{activity_id}/progress"
    client.cookies.clear()
    assert client.post(f"{base}/start", headers=HEADERS).status_code == 401

    student = auth(client, "progress-student@example.com")
    assert client.post(f"{base}/start", headers=HEADERS).status_code == 404

    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    client.post(f"{course_path}/publish", headers=HEADERS)
    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.post(f"{base}/start", headers=HEADERS).status_code == 404
    client.post(enrollment_path(course_id), headers=HEADERS)

    assert client.post(f"{base}/complete", headers=HEADERS).status_code == 409
    started = client.post(f"{base}/start", headers=HEADERS)
    repeated_start = client.post(f"{base}/start", headers=HEADERS)
    assert started.status_code == repeated_start.status_code == 200
    assert (
        started.json()
        == repeated_start.json()
        == {
            "activity_id": activity_id,
            "status": "in_progress",
        }
    )
    completed = client.post(f"{base}/complete", headers=HEADERS)
    repeated_complete = client.post(f"{base}/complete", headers=HEADERS)
    assert (
        completed.json()
        == repeated_complete.json()
        == {
            "activity_id": activity_id,
            "status": "completed",
        }
    )
    assert client.get(base).json() == completed.json()

    with Factory() as session:
        enrollment = session.scalar(
            select(EnrollmentModel).where(EnrollmentModel.course_id == UUID(course_id))
        )
        assert enrollment is not None
        session.delete(enrollment)
        session.commit()
    assert client.get(base).status_code == 404
    client.post(enrollment_path(course_id), headers=HEADERS)
    assert client.get(base).json() == completed.json()

    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    client.post(f"{course_path}/archive", headers=HEADERS)
    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.post(f"{base}/start", headers=HEADERS).status_code == 404
    assert client.get(base).status_code == 404

    auth(client, "progress-other@example.com")
    assert client.get(base).status_code == 404
    unknown = "/api/v1/student/activities/00000000-0000-0000-0000-000000000000/progress"
    assert client.post(f"{unknown}/start", headers=HEADERS).status_code == 404


def test_activity_progress_openapi_contract(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    base = "/api/v1/student/activities/{activity_id}/progress"
    assert set(openapi["paths"][base]) == {"get"}
    assert set(openapi["paths"][f"{base}/start"]) == {"post"}
    assert set(openapi["paths"][f"{base}/complete"]) == {"post"}
    assert "ActivityProgressResponse" in openapi["components"]["schemas"]


def test_student_course_progress_contract_and_calculation(client: TestClient) -> None:
    path = "/api/v1/student/courses/00000000-0000-0000-0000-000000000000/progress"
    assert client.get(path).status_code == 401

    teacher = auth(client, "course-progress-teacher@example.com")
    course_path, course_id = create_course(client, "Course Progress")
    first_activity = create_activity(client, course_path)
    second_activity = create_activity(client, course_path)
    third_activity = create_activity(client, course_path)
    client.post(f"{course_path}/publish", headers=HEADERS)

    other_path, other_course_id = create_course(client, "Other Course")
    other_activity = create_activity(client, other_path)
    client.post(f"{other_path}/publish", headers=HEADERS)

    student = auth(client, "course-progress-student@example.com")
    endpoint = f"/api/v1/student/courses/{course_id}/progress"
    assert client.get(endpoint).status_code == 404
    client.post(enrollment_path(course_id), headers=HEADERS)
    client.post(enrollment_path(other_course_id), headers=HEADERS)

    published_activities = [
        activity
        for section in client.get(f"/api/v1/student/courses/{course_id}").json()["sections"]
        for unit in section["units"]
        for activity in unit["activities"]
    ]
    assert len(published_activities) == 3
    assert all(activity["contents"] == [] for activity in published_activities)

    assert client.get(endpoint).json() == {
        "course_id": course_id,
        "completed_activities": 0,
        "total_activities": 3,
        "progress_percent": 0,
    }
    for activity_id in (first_activity, other_activity):
        progress = f"/api/v1/student/activities/{activity_id}/progress"
        client.post(f"{progress}/start", headers=HEADERS)
        client.post(f"{progress}/complete", headers=HEADERS)

    assert client.get(endpoint).json() == {
        "course_id": course_id,
        "completed_activities": 1,
        "total_activities": 3,
        "progress_percent": 33,
    }
    for activity_id in (second_activity, third_activity):
        progress = f"/api/v1/student/activities/{activity_id}/progress"
        client.post(f"{progress}/start", headers=HEADERS)
        client.post(f"{progress}/complete", headers=HEADERS)
    assert client.get(endpoint).json() == {
        "course_id": course_id,
        "completed_activities": 3,
        "total_activities": 3,
        "progress_percent": 100,
    }

    unknown = "/api/v1/student/courses/00000000-0000-0000-0000-000000000000/progress"
    assert client.get(unknown).status_code == 404
    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    client.post(f"{course_path}/archive", headers=HEADERS)
    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.get(endpoint).status_code == 404


def test_student_course_progress_zero_activity_course_cannot_be_published(
    client: TestClient,
) -> None:
    teacher = auth(client, "empty-progress-teacher@example.com")
    course_path, course_id = create_course(client, "Empty Course")

    response = client.post(f"{course_path}/publish", headers=HEADERS)
    assert response.status_code == 409
    assert response.json() == {"detail": "Course is not ready for publication"}

    auth(client, "empty-progress-student@example.com")
    assert client.post(enrollment_path(course_id), headers=HEADERS).status_code == 404
    assert (
        client.get(f"/api/v1/student/courses/{course_id}/progress").status_code == 404
    )
    client.cookies.set(SESSION_COOKIE_NAME, teacher)


def test_student_course_progress_openapi_contract(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/v1/student/courses/{course_id}/progress"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CourseProgressResponse"
    }
    schema = openapi["components"]["schemas"]["CourseProgressResponse"]
    assert set(schema["properties"]) == {
        "course_id",
        "completed_activities",
        "total_activities",
        "progress_percent",
    }
    assert set(schema["required"]) == set(schema["properties"])


def test_student_dashboard_empty_and_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/student/dashboard").status_code == 401
    auth(client, "empty-dashboard@example.com")
    response = client.get("/api/v1/student/dashboard")
    assert response.status_code == 200
    assert response.json() == {"my_courses": [], "continue_learning": None}


def test_student_dashboard_composes_enrollment_and_continue_learning(
    client: TestClient,
) -> None:
    teacher = auth(client, "dashboard-teacher@example.com")
    course_path, course_id = create_course(client, "Dashboard Course")
    activity_id = create_activity(client, course_path)
    client.post(f"{course_path}/publish", headers=HEADERS)

    other_path, _other_course_id = create_course(client, "Not Enrolled")
    create_activity(client, other_path)
    client.post(f"{other_path}/publish", headers=HEADERS)

    student = auth(client, "dashboard-student@example.com")
    client.post(enrollment_path(course_id), headers=HEADERS)
    client.post(
        f"/api/v1/student/activities/{activity_id}/progress/start",
        headers=HEADERS,
    )
    response = client.get("/api/v1/student/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["my_courses"]) == 1
    assert payload["my_courses"][0]["course_id"] == course_id
    assert payload["my_courses"][0]["title"] == "Dashboard Course"
    assert payload["my_courses"][0]["status"] == "enrolled"
    assert payload["continue_learning"] == {
        "course_id": course_id,
        "activity_id": activity_id,
        "activity_title": "Activity",
        "status": "in_progress",
        "updated_at": payload["continue_learning"]["updated_at"],
    }
    assert set(payload) == {"my_courses", "continue_learning"}

    auth(client, "dashboard-other-student@example.com")
    assert client.get("/api/v1/student/dashboard").json() == {
        "my_courses": [],
        "continue_learning": None,
    }
    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    client.cookies.set(SESSION_COOKIE_NAME, student)


def test_student_dashboard_excludes_archived_enrolled_course(client: TestClient) -> None:
    teacher = auth(client, "stale-dashboard-teacher@example.com")
    course_path, course_id = create_course(client, "Archived Enrollment")
    create_activity(client, course_path)
    client.post(f"{course_path}/publish", headers=HEADERS)
    student = auth(client, "stale-dashboard-student@example.com")
    client.post(enrollment_path(course_id), headers=HEADERS)

    client.cookies.set(SESSION_COOKIE_NAME, teacher)
    client.post(f"{course_path}/archive", headers=HEADERS)
    client.cookies.set(SESSION_COOKIE_NAME, student)
    assert client.get("/api/v1/student/dashboard").json() == {
        "my_courses": [],
        "continue_learning": None,
    }


def test_student_dashboard_openapi_contract(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/v1/student/dashboard"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/StudentDashboardResponse"
    }
    continue_schema = openapi["components"]["schemas"][
        "DashboardContinueLearningResponse"
    ]
    assert "activity_title" in continue_schema["properties"]
    assert "activity_title" in continue_schema["required"]
