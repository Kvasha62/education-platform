from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.education.application.errors import LinkedContentUnavailableError
from app.education.composition import get_published_course_reader
from app.identity.api.dependencies import SESSION_COOKIE_NAME
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
    assert (
        client.post(
            "/api/v1/auth/register", json={"email": email, "password": "a secure password"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": email, "password": "a secure password"}
        ).status_code
        == 200
    )
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return token


def use(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)


def create_course(client: TestClient, title: str = "Course") -> tuple[str, str]:
    space = client.post("/api/v1/teacher-spaces", json={"name": "Space"}, headers=HEADERS).json()
    environment = f"/api/v1/teacher-spaces/{space['id']}/environment"
    client.post(environment, json={"name": "Environment"}, headers=HEADERS)
    course = client.post(f"{environment}/courses", json={"title": title}, headers=HEADERS).json()
    return space["id"], course["id"]


def course_paths(space_id: str, course_id: str) -> tuple[str, str]:
    course = f"/api/v1/teacher-spaces/{space_id}/environment/courses/{course_id}"
    return course, f"{course}/sections"


def test_authentication_and_published_visibility(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/student/courses/{missing}").status_code == 401

    teacher_token = auth(client, "teacher@example.com")
    space_id, draft_id = create_course(client, "Draft")
    student_token = auth(client, "student@example.com")
    assert client.get(f"/api/v1/student/courses/{draft_id}").status_code == 404
    assert client.get(f"/api/v1/student/courses/{missing}").status_code == 404

    use(client, teacher_token)
    course_path, _ = course_paths(space_id, draft_id)
    assert client.post(f"{course_path}/publish", headers=HEADERS).status_code == 200
    use(client, student_token)
    assert client.get(f"/api/v1/student/courses/{draft_id}").status_code == 200

    use(client, teacher_token)
    assert client.post(f"{course_path}/archive", headers=HEADERS).status_code == 200
    use(client, student_token)
    assert client.get(f"/api/v1/student/courses/{draft_id}").status_code == 404


def test_student_reads_ordered_structure_and_only_published_content(client: TestClient) -> None:
    teacher_token = auth(client, "teacher@example.com")
    space_id, course_id = create_course(client, "Published Course")
    course_path, sections_path = course_paths(space_id, course_id)

    late_section = client.post(
        sections_path, json={"title": "Late", "position": 2}, headers=HEADERS
    ).json()
    early_section = client.post(
        sections_path, json={"title": "Early", "position": 0}, headers=HEADERS
    ).json()
    early_units = f"{sections_path}/{early_section['id']}/units"
    late_unit = client.post(
        early_units, json={"title": "Late Unit", "position": 3}, headers=HEADERS
    ).json()
    early_unit = client.post(
        early_units, json={"title": "Early Unit", "position": 1}, headers=HEADERS
    ).json()
    activities = f"{early_units}/{early_unit['id']}/activities"
    late_activity = client.post(
        activities,
        json={"title": "Late Activity", "type": "video", "position": 5},
        headers=HEADERS,
    ).json()
    early_activity = client.post(
        activities,
        json={"title": "Early Activity", "type": "lecture", "position": 0},
        headers=HEADERS,
    ).json()

    draft_content = client.post(
        "/api/v1/contents",
        json={"title": "Draft Content", "type": "article"},
        headers=HEADERS,
    ).json()
    published_content = client.post(
        "/api/v1/contents",
        json={"title": "Published Content", "type": "resource"},
        headers=HEADERS,
    ).json()
    client.put(
        f"/api/v1/contents/{published_content['id']}/body",
        json={
            "schema_version": 1,
            "kind": "resource",
            "resource": {"url": "https://example.test/material", "description": ""},
        },
        headers=HEADERS,
    )
    client.post(f"/api/v1/contents/{published_content['id']}/publish", headers=HEADERS)
    links = f"{activities}/{early_activity['id']}/contents"
    client.post(links, json={"content_id": draft_content["id"]}, headers=HEADERS)
    client.post(links, json={"content_id": published_content["id"]}, headers=HEADERS)
    client.post(f"{course_path}/publish", headers=HEADERS)

    student_token = auth(client, "student@example.com")
    use(client, student_token)
    response = client.get(f"/api/v1/student/courses/{course_id}")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"id", "title", "sections"}
    assert [item["id"] for item in payload["sections"]] == [
        early_section["id"],
        late_section["id"],
    ]
    assert [item["id"] for item in payload["sections"][0]["units"]] == [
        early_unit["id"],
        late_unit["id"],
    ]
    assert payload["sections"][1]["units"] == []
    assert payload["sections"][0]["units"][1]["activities"] == []
    returned_activities = payload["sections"][0]["units"][0]["activities"]
    assert [item["id"] for item in returned_activities] == [
        early_activity["id"],
        late_activity["id"],
    ]
    assert set(returned_activities[0]) == {"id", "title", "type", "position", "contents"}
    assert returned_activities[1]["contents"] == []
    assert returned_activities[0]["contents"] == [
        {
            "id": published_content["id"],
            "type": "resource",
            "status": "published",
            "available_for_student": True,
        }
    ]
    assert draft_content["id"] not in str(payload)
    assert "created_at" not in str(payload)
    assert "updated_at" not in str(payload)
    assert "owner_user_id" not in str(payload)
    assert "teacher_space_id" not in str(payload)
    assert late_section["id"] in str(payload)
    use(client, teacher_token)


def test_published_course_with_empty_structure_returns_empty_lists(client: TestClient) -> None:
    teacher_token = auth(client, "teacher@example.com")
    space_id, course_id = create_course(client, "Empty")
    course_path, _ = course_paths(space_id, course_id)
    client.post(f"{course_path}/publish", headers=HEADERS)

    auth(client, "student@example.com")
    response = client.get(f"/api/v1/student/courses/{course_id}")
    assert response.status_code == 200
    assert response.json()["sections"] == []
    use(client, teacher_token)


class FailingPublishedCourseReader:
    def get_published(self, course_id):
        raise LinkedContentUnavailableError


def test_content_lookup_failure_returns_503(client: TestClient) -> None:
    auth(client, "student@example.com")
    app.dependency_overrides[get_published_course_reader] = FailingPublishedCourseReader
    try:
        response = client.get("/api/v1/student/courses/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_published_course_reader, None)


def test_openapi_contains_exact_student_contract(client: TestClient) -> None:
    path = "/api/v1/student/courses/{course_id}"
    openapi = client.get("/openapi.json").json()
    assert set(openapi["paths"][path]) == {"get"}
    assert "StudentCourseResponse" in openapi["components"]["schemas"]


def test_published_course_collection_auth_visibility_ordering_and_shape(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/student/courses").status_code == 401

    teacher_token = auth(client, "list-teacher@example.com")
    _draft_space, draft_id = create_course(client, "Draft")
    first_space, first_id = create_course(client, "First Published")
    first_path, _ = course_paths(first_space, first_id)
    client.post(f"{first_path}/publish", headers=HEADERS)
    second_space, second_id = create_course(client, "Second Published")
    second_path, _ = course_paths(second_space, second_id)
    client.post(f"{second_path}/publish", headers=HEADERS)
    archived_space, archived_id = create_course(client, "Archived")
    archived_path, _ = course_paths(archived_space, archived_id)
    client.post(f"{archived_path}/publish", headers=HEADERS)
    client.post(f"{archived_path}/archive", headers=HEADERS)

    student_token = auth(client, "list-student@example.com")
    response = client.get("/api/v1/student/courses")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": second_id, "title": "Second Published"},
            {"id": first_id, "title": "First Published"},
        ]
    }
    assert draft_id not in response.text
    assert archived_id not in response.text
    use(client, teacher_token)
    use(client, student_token)


def test_empty_published_course_collection_returns_200(client: TestClient) -> None:
    auth(client, "empty-course-list@example.com")
    response = client.get("/api/v1/student/courses")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_openapi_contains_exact_published_course_list_contract(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/v1/student/courses"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PublishedCourseListResponse"
    }
