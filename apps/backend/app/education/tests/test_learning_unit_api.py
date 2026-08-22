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
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
ORIGIN = "http://frontend.test"
HEADERS = {"Origin": ORIGIN}


def override_db() -> Generator[Session, None, None]:
    with SessionFactory() as session:
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
    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def auth(client: TestClient, email: str) -> None:
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
    assert client.cookies.get(SESSION_COOKIE_NAME)


def setup(client: TestClient, name: str = "Space") -> tuple[str, str, str]:
    space = client.post("/api/v1/teacher-spaces", json={"name": name}, headers=HEADERS).json()
    client.post(
        f"/api/v1/teacher-spaces/{space['id']}/environment", json={"name": "Env"}, headers=HEADERS
    )
    courses = f"/api/v1/teacher-spaces/{space['id']}/environment/courses"
    course = client.post(courses, json={"title": "Course"}, headers=HEADERS).json()
    sections = f"{courses}/{course['id']}/sections"
    section = client.post(
        sections, json={"title": "Section", "position": 0}, headers=HEADERS
    ).json()
    return space["id"], course["id"], section["id"]


def path(space: str, course: str, section: str) -> str:
    return f"/api/v1/teacher-spaces/{space}/environment/courses/{course}/sections/{section}/units"


def create(client: TestClient, base: str, title: str, position: int):
    return client.post(base, json={"title": title, "position": position}, headers=HEADERS)


@pytest.mark.parametrize("method", ["post", "get", "patch", "delete"])
def test_authentication_required(client: TestClient, method: str) -> None:
    base = path(*(["00000000-0000-0000-0000-000000000000"] * 3))
    target = base if method in {"post", "get"} else f"{base}/00000000-0000-0000-0000-000000000000"
    response = client.request(
        method, target, json={"title": "Unit", "position": 0}, headers=HEADERS
    )
    assert response.status_code == 401


def test_crud_order_and_empty_list(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = path(*setup(client))
    assert client.get(base).json() == []
    last = create(client, base, "Last", 5).json()
    tied = [create(client, base, "B", 0).json(), create(client, base, "A", 0).json()]
    listed = client.get(base).json()
    ordered = sorted(tied, key=lambda unit: unit["id"])
    assert [unit["id"] for unit in listed] == [ordered[0]["id"], ordered[1]["id"], last["id"]]
    item = f"{base}/{last['id']}"
    assert client.get(item).status_code == 200
    assert client.patch(item, json={"title": "Updated"}, headers=HEADERS).json()["position"] == 5
    assert client.patch(item, json={"position": 1000}, headers=HEADERS).json()["position"] == 1000
    assert client.delete(item, headers=HEADERS).status_code == 204
    assert client.get(item).status_code == 404


def test_validation_and_immutable_relationship(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = path(*setup(client))
    assert create(client, base, " ", 0).status_code == 422
    assert create(client, base, "x" * 121, 0).status_code == 422
    assert create(client, base, "Unit", -1).status_code == 422
    unit = create(client, base, "Unit", 0).json()
    item = f"{base}/{unit['id']}"
    assert client.patch(item, json={}, headers=HEADERS).status_code == 422
    assert client.patch(item, json={"title": None}, headers=HEADERS).status_code == 422
    assert client.patch(item, json={"position": None}, headers=HEADERS).status_code == 422
    assert client.patch(item, json={"unknown": 1}, headers=HEADERS).status_code == 422
    assert (
        client.patch(item, json={"section_id": unit["section_id"]}, headers=HEADERS).status_code
        == 422
    )
    assert (
        client.post(
            base, json={"title": "X", "position": 0, "owner_id": "x"}, headers=HEADERS
        ).status_code
        == 422
    )


def test_non_owner_and_cross_scope_return_404(client: TestClient) -> None:
    auth(client, "owner@example.com")
    first = setup(client, "First")
    base = path(*first)
    unit = create(client, base, "Private", 0).json()
    second = setup(client, "Second")
    wrong_section = f"{path(*second)}/{unit['id']}"
    assert client.get(wrong_section).status_code == 404
    # Same environment, different Course and Section.
    space = first[0]
    courses = f"/api/v1/teacher-spaces/{space}/environment/courses"
    other_course = client.post(courses, json={"title": "Other"}, headers=HEADERS).json()
    sections = f"{courses}/{other_course['id']}/sections"
    other_section = client.post(
        sections, json={"title": "Other", "position": 0}, headers=HEADERS
    ).json()
    assert (
        client.get(
            f"{path(space, other_course['id'], other_section['id'])}/{unit['id']}"
        ).status_code
        == 404
    )
    first_course_sections = (
        f"/api/v1/teacher-spaces/{space}/environment/courses/{first[1]}/sections"
    )
    other_section_same_course = client.post(
        first_course_sections,
        json={"title": "Sibling", "position": 1},
        headers=HEADERS,
    ).json()
    assert (
        client.get(
            f"{path(space, first[1], other_section_same_course['id'])}/{unit['id']}"
        ).status_code
        == 404
    )
    auth(client, "other@example.com")
    item = f"{base}/{unit['id']}"
    assert client.get(base).status_code == 404
    assert client.get(item).status_code == 404
    assert create(client, base, "Stolen", 0).status_code == 404
    assert client.patch(item, json={"title": "Stolen"}, headers=HEADERS).status_code == 404
    assert client.delete(item, headers=HEADERS).status_code == 404


def test_missing_parents_and_unit_return_404(client: TestClient) -> None:
    auth(client, "owner@example.com")
    missing = "00000000-0000-0000-0000-000000000000"
    space = client.post("/api/v1/teacher-spaces", json={"name": "No Env"}, headers=HEADERS).json()[
        "id"
    ]
    assert create(client, path(space, missing, missing), "Missing", 0).status_code == 404
    client.post(
        f"/api/v1/teacher-spaces/{space}/environment",
        json={"name": "Environment"},
        headers=HEADERS,
    )
    assert create(client, path(space, missing, missing), "Missing", 0).status_code == 404
    courses = f"/api/v1/teacher-spaces/{space}/environment/courses"
    course = client.post(courses, json={"title": "Course"}, headers=HEADERS).json()
    assert create(client, path(space, course["id"], missing), "Missing", 0).status_code == 404

    valid = setup(client)
    base = path(*valid)
    item = f"{base}/{missing}"
    assert client.get(item).status_code == 404
    assert client.patch(item, json={"title": "Missing"}, headers=HEADERS).status_code == 404
    assert client.delete(item, headers=HEADERS).status_code == 404


def test_disabled_space_is_read_only(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup(client)
    base = path(*values)
    unit = create(client, base, "Readable", 0).json()
    client.post(f"/api/v1/teacher-spaces/{values[0]}/disable", headers=HEADERS)
    item = f"{base}/{unit['id']}"
    assert client.get(base).status_code == 200
    assert client.get(item).status_code == 200
    assert create(client, base, "No", 1).status_code == 409
    assert client.patch(item, json={"title": "No"}, headers=HEADERS).status_code == 409
    assert client.delete(item, headers=HEADERS).status_code == 409


def test_openapi_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    collection = "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}/sections/{section_id}/units"
    item = f"{collection}/{{unit_id}}"
    assert {"post", "get"} <= paths[collection].keys()
    assert {"get", "patch", "delete"} <= paths[item].keys()
