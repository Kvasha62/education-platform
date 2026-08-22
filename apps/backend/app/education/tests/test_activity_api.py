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


def setup(client: TestClient, name: str = "Space") -> tuple[str, str, str, str]:
    space = client.post("/api/v1/teacher-spaces", json={"name": name}, headers=HEADERS).json()
    env = f"/api/v1/teacher-spaces/{space['id']}/environment"
    client.post(env, json={"name": "Env"}, headers=HEADERS)
    course = client.post(f"{env}/courses", json={"title": "Course"}, headers=HEADERS).json()
    sections = f"{env}/courses/{course['id']}/sections"
    section = client.post(
        sections, json={"title": "Section", "position": 0}, headers=HEADERS
    ).json()
    units = f"{sections}/{section['id']}/units"
    unit = client.post(units, json={"title": "Unit", "position": 0}, headers=HEADERS).json()
    return space["id"], course["id"], section["id"], unit["id"]


def path(values: tuple[str, str, str, str]) -> str:
    space, course, section, unit = values
    return f"/api/v1/teacher-spaces/{space}/environment/courses/{course}/sections/{section}/units/{unit}/activities"


def create(
    client: TestClient, base: str, kind: str = "lecture", title: str = "Activity", position: int = 0
):
    return client.post(
        base, json={"title": title, "type": kind, "position": position}, headers=HEADERS
    )


@pytest.mark.parametrize("method", ["post", "get", "patch", "delete"])
def test_auth_required(client: TestClient, method: str) -> None:
    ids = ("00000000-0000-0000-0000-000000000000",) * 4
    base = path(ids)
    target = base if method in {"post", "get"} else f"{base}/{ids[0]}"
    assert (
        client.request(
            method, target, json={"title": "A", "type": "lecture", "position": 0}, headers=HEADERS
        ).status_code
        == 401
    )


def test_crud_types_order_and_empty(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = path(setup(client))
    assert client.get(base).json() == []
    items = [
        create(client, base, kind, kind, 0).json() for kind in ("lecture", "video", "homework")
    ]
    last = create(client, base, "video", "Last", 5).json()
    expected = sorted(items, key=lambda item: item["id"])
    assert [x["id"] for x in client.get(base).json()] == [*[x["id"] for x in expected], last["id"]]
    item = f"{base}/{last['id']}"
    assert client.get(item).status_code == 200
    both = client.patch(item, json={"title": "Changed", "position": 9}, headers=HEADERS).json()
    assert (both["title"], both["position"], both["type"]) == ("Changed", 9, "video")
    assert client.delete(item, headers=HEADERS).status_code == 204
    assert client.get(item).status_code == 404


def test_activity_lists_are_isolated_between_units_in_same_section(
    client: TestClient,
) -> None:
    auth(client, "owner@example.com")
    space, course, section, first_unit = setup(client)
    first_path = path((space, course, section, first_unit))
    first_activity = create(client, first_path, "lecture", "First Activity", 0).json()

    units_path = (
        f"/api/v1/teacher-spaces/{space}/environment/courses/{course}"
        f"/sections/{section}/units"
    )
    second_unit = client.post(
        units_path,
        json={"title": "Second Unit", "position": 1},
        headers=HEADERS,
    ).json()
    second_path = path((space, course, section, second_unit["id"]))
    second_activity = create(client, second_path, "video", "Second Activity", 0).json()

    first_list = client.get(first_path).json()
    second_list = client.get(second_path).json()
    assert [item["id"] for item in first_list] == [first_activity["id"]]
    assert [item["id"] for item in second_list] == [second_activity["id"]]
    assert second_activity["id"] not in {item["id"] for item in first_list}
    assert first_activity["id"] not in {item["id"] for item in second_list}


def test_patch_and_create_validation(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = path(setup(client))
    assert create(client, base, "invalid").status_code == 422
    assert create(client, base, title=" ").status_code == 422
    assert create(client, base, position=-1).status_code == 422
    item = f"{base}/{create(client, base).json()['id']}"
    for payload in (
        {},
        {"title": None},
        {"position": None},
        {"title": "X", "position": None},
        {"type": "video"},
        {"unknown": 1},
        {"learning_unit_id": "x"},
        {"owner_id": "x"},
    ):
        assert client.patch(item, json=payload, headers=HEADERS).status_code == 422
    assert client.patch(item, json={"title": "Only title"}, headers=HEADERS).status_code == 200
    assert client.patch(item, json={"position": 999}, headers=HEADERS).status_code == 200


def test_cross_scope_and_non_owner_are_404(client: TestClient) -> None:
    auth(client, "owner@example.com")
    first = setup(client, "First")
    base = path(first)
    activity = create(client, base).json()
    second = setup(client, "Second")
    assert client.get(f"{path(second)}/{activity['id']}").status_code == 404
    # Cross learning-unit inside same Section.
    space, course, section, _ = first
    units = f"/api/v1/teacher-spaces/{space}/environment/courses/{course}/sections/{section}/units"
    sibling = client.post(units, json={"title": "Sibling", "position": 1}, headers=HEADERS).json()
    sibling_path = path((space, course, section, sibling["id"]))
    assert client.get(f"{sibling_path}/{activity['id']}").status_code == 404
    space, course, section, _ = first
    env = f"/api/v1/teacher-spaces/{space}/environment"
    other_course = client.post(f"{env}/courses", json={"title": "Other"}, headers=HEADERS).json()
    other_sections = f"{env}/courses/{other_course['id']}/sections"
    other_section = client.post(
        other_sections, json={"title": "Other", "position": 0}, headers=HEADERS
    ).json()
    other_units = f"{other_sections}/{other_section['id']}/units"
    other_unit = client.post(
        other_units, json={"title": "Other", "position": 0}, headers=HEADERS
    ).json()
    assert (
        client.get(
            f"{path((space, other_course['id'], other_section['id'], other_unit['id']))}/{activity['id']}"
        ).status_code
        == 404
    )
    same_course_sections = f"{env}/courses/{course}/sections"
    sibling_section = client.post(
        same_course_sections, json={"title": "Sibling", "position": 1}, headers=HEADERS
    ).json()
    sibling_units = f"{same_course_sections}/{sibling_section['id']}/units"
    sibling_unit = client.post(
        sibling_units, json={"title": "Sibling", "position": 0}, headers=HEADERS
    ).json()
    assert (
        client.get(
            f"{path((space, course, sibling_section['id'], sibling_unit['id']))}/{activity['id']}"
        ).status_code
        == 404
    )
    auth(client, "other@example.com")
    item = f"{base}/{activity['id']}"
    assert client.get(base).status_code == 404
    assert client.get(item).status_code == 404
    assert create(client, base).status_code == 404
    assert client.patch(item, json={"title": "X"}, headers=HEADERS).status_code == 404
    assert client.delete(item, headers=HEADERS).status_code == 404


def test_missing_parent_and_activity(client: TestClient) -> None:
    auth(client, "owner@example.com")
    missing = "00000000-0000-0000-0000-000000000000"
    space = client.post("/api/v1/teacher-spaces", json={"name": "No Env"}, headers=HEADERS).json()[
        "id"
    ]
    assert create(client, path((space, missing, missing, missing))).status_code == 404
    base = path(setup(client))
    item = f"{base}/{missing}"
    assert client.get(item).status_code == 404
    assert client.patch(item, json={"title": "X"}, headers=HEADERS).status_code == 404
    assert client.delete(item, headers=HEADERS).status_code == 404


def test_disabled_read_only(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup(client)
    base = path(values)
    activity = create(client, base).json()
    client.post(f"/api/v1/teacher-spaces/{values[0]}/disable", headers=HEADERS)
    item = f"{base}/{activity['id']}"
    assert client.get(base).status_code == 200
    assert client.get(item).status_code == 200
    assert create(client, base).status_code == 409
    assert client.patch(item, json={"title": "X"}, headers=HEADERS).status_code == 409
    assert client.delete(item, headers=HEADERS).status_code == 409


def test_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    collection = "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}/sections/{section_id}/units/{unit_id}/activities"
    assert {"post", "get"} <= paths[collection].keys()
    assert {"get", "patch", "delete"} <= paths[f"{collection}/{{activity_id}}"].keys()
