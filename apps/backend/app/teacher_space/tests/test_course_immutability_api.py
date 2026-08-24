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


def setup(client: TestClient) -> dict[str, str]:
    space = client.post("/api/v1/teacher-spaces", json={"name": "Space"}, headers=HEADERS).json()
    environment = f"/api/v1/teacher-spaces/{space['id']}/environment"
    client.post(environment, json={"name": "Environment"}, headers=HEADERS)
    courses = f"{environment}/courses"
    course = client.post(courses, json={"title": "Course"}, headers=HEADERS).json()
    sections = f"{courses}/{course['id']}/sections"
    section = client.post(
        sections, json={"title": "Section", "position": 0}, headers=HEADERS
    ).json()
    units = f"{sections}/{section['id']}/units"
    unit = client.post(units, json={"title": "Unit", "position": 0}, headers=HEADERS).json()
    activities = f"{units}/{unit['id']}/activities"
    activity = client.post(
        activities,
        json={"title": "Activity", "type": "lecture", "position": 0},
        headers=HEADERS,
    ).json()
    content = client.post(
        "/api/v1/contents",
        json={"title": "Content", "type": "article"},
        headers=HEADERS,
    ).json()
    links = f"{activities}/{activity['id']}/contents"
    assert (
        client.post(links, json={"content_id": content["id"]}, headers=HEADERS).status_code == 200
    )
    return {
        "space": space["id"],
        "course": course["id"],
        "section": section["id"],
        "unit": unit["id"],
        "activity": activity["id"],
        "content": content["id"],
        "courses": courses,
        "sections": sections,
        "units": units,
        "activities": activities,
        "links": links,
    }


def test_draft_course_remains_fully_mutable(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup(client)
    course_path = f"{values['courses']}/{values['course']}"
    assert client.patch(course_path, json={"title": "Changed"}, headers=HEADERS).status_code == 200

    section = client.post(
        values["sections"], json={"title": "Temporary", "position": 1}, headers=HEADERS
    ).json()
    section_path = f"{values['sections']}/{section['id']}"
    assert client.patch(section_path, json={"title": "Updated"}, headers=HEADERS).status_code == 200
    assert client.delete(section_path, headers=HEADERS).status_code == 204

    unit = client.post(
        values["units"], json={"title": "Temporary", "position": 1}, headers=HEADERS
    ).json()
    unit_path = f"{values['units']}/{unit['id']}"
    assert client.patch(unit_path, json={"title": "Updated"}, headers=HEADERS).status_code == 200
    assert client.delete(unit_path, headers=HEADERS).status_code == 204

    activity = client.post(
        values["activities"],
        json={"title": "Temporary", "type": "video", "position": 1},
        headers=HEADERS,
    ).json()
    activity_path = f"{values['activities']}/{activity['id']}"
    assert (
        client.patch(activity_path, json={"title": "Updated"}, headers=HEADERS).status_code == 200
    )
    assert client.delete(activity_path, headers=HEADERS).status_code == 204

    assert (
        client.delete(f"{values['links']}/{values['content']}", headers=HEADERS).status_code == 204
    )
    assert (
        client.post(
            values["links"], json={"content_id": values["content"]}, headers=HEADERS
        ).status_code
        == 200
    )


def assert_structure_mutations_blocked(client: TestClient, values: dict[str, str]) -> None:
    course_path = f"{values['courses']}/{values['course']}"
    section_path = f"{values['sections']}/{values['section']}"
    unit_path = f"{values['units']}/{values['unit']}"
    activity_path = f"{values['activities']}/{values['activity']}"

    responses = [
        client.patch(course_path, json={"title": "Blocked"}, headers=HEADERS),
        client.post(values["sections"], json={"title": "Blocked", "position": 1}, headers=HEADERS),
        client.patch(section_path, json={"title": "Blocked"}, headers=HEADERS),
        client.delete(section_path, headers=HEADERS),
        client.post(values["units"], json={"title": "Blocked", "position": 1}, headers=HEADERS),
        client.patch(unit_path, json={"title": "Blocked"}, headers=HEADERS),
        client.delete(unit_path, headers=HEADERS),
        client.post(
            values["activities"],
            json={"title": "Blocked", "type": "video", "position": 1},
            headers=HEADERS,
        ),
        client.patch(activity_path, json={"title": "Blocked"}, headers=HEADERS),
        client.delete(activity_path, headers=HEADERS),
        client.post(values["links"], json={"content_id": values["content"]}, headers=HEADERS),
        client.delete(f"{values['links']}/{values['content']}", headers=HEADERS),
    ]
    assert all(response.status_code == 409 for response in responses)


def test_published_and_archived_course_structure_is_read_only(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup(client)
    course_path = f"{values['courses']}/{values['course']}"

    assert client.post(f"{course_path}/publish", headers=HEADERS).status_code == 200
    assert client.post(f"{course_path}/publish", headers=HEADERS).status_code == 200
    assert_structure_mutations_blocked(client, values)
    assert client.get(course_path).status_code == 200
    assert client.get(values["sections"]).status_code == 200
    assert client.get(values["units"]).status_code == 200
    assert client.get(values["activities"]).status_code == 200
    assert client.get(values["links"]).status_code == 200

    assert client.post(f"{course_path}/archive", headers=HEADERS).status_code == 200
    assert client.post(f"{course_path}/archive", headers=HEADERS).status_code == 200
    assert_structure_mutations_blocked(client, values)
    assert client.get(values["links"]).status_code == 200


def test_ownership_isolation_precedes_immutability(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup(client)
    course_path = f"{values['courses']}/{values['course']}"
    assert client.post(f"{course_path}/publish", headers=HEADERS).status_code == 200

    missing = "00000000-0000-0000-0000-000000000000"
    assert (
        client.patch(
            f"{values['sections']}/{missing}", json={"title": "Hidden"}, headers=HEADERS
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"{values['units']}/{missing}", json={"title": "Hidden"}, headers=HEADERS
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"{values['activities']}/{missing}", json={"title": "Hidden"}, headers=HEADERS
        ).status_code
        == 404
    )
    missing_links = f"{values['activities']}/{missing}/contents"
    assert (
        client.post(
            missing_links, json={"content_id": values["content"]}, headers=HEADERS
        ).status_code
        == 404
    )

    second_space = client.post(
        "/api/v1/teacher-spaces", json={"name": "Second"}, headers=HEADERS
    ).json()
    second_environment = f"/api/v1/teacher-spaces/{second_space['id']}/environment"
    client.post(second_environment, json={"name": "Second"}, headers=HEADERS)
    wrong_course_path = f"{second_environment}/courses/{values['course']}"
    assert (
        client.patch(wrong_course_path, json={"title": "Hidden"}, headers=HEADERS).status_code
        == 404
    )
    assert (
        client.post(
            f"{wrong_course_path}/sections",
            json={"title": "Hidden", "position": 1},
            headers=HEADERS,
        ).status_code
        == 404
    )

    auth(client, "other@example.com")
    assert client.patch(course_path, json={"title": "Hidden"}, headers=HEADERS).status_code == 404
    assert (
        client.post(
            values["sections"], json={"title": "Hidden", "position": 1}, headers=HEADERS
        ).status_code
        == 404
    )
    assert (
        client.post(
            values["links"], json={"content_id": values["content"]}, headers=HEADERS
        ).status_code
        == 404
    )
