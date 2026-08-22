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


def create_teacher_space(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/v1/teacher-spaces", json={"name": name}, headers=MUTATION_HEADERS
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_environment(client: TestClient, teacher_space_id: str) -> None:
    assert client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/environment",
        json={"name": "Environment"},
        headers=MUTATION_HEADERS,
    ).status_code == 201


def create_course(client: TestClient, teacher_space_id: str, title: str) -> str:
    response = client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/environment/courses",
        json={"title": title},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 201
    return response.json()["id"]


def sections_path(teacher_space_id: str, course_id: str) -> str:
    return (
        f"/api/v1/teacher-spaces/{teacher_space_id}/environment"
        f"/courses/{course_id}/sections"
    )


def create_section(
    client: TestClient, teacher_space_id: str, course_id: str, title: str, position: int
):
    return client.post(
        sections_path(teacher_space_id, course_id),
        json={"title": title, "position": position},
        headers=MUTATION_HEADERS,
    )


def setup_course(client: TestClient, space_name: str = "Space") -> tuple[str, str]:
    teacher_space_id = create_teacher_space(client, space_name)
    create_environment(client, teacher_space_id)
    return teacher_space_id, create_course(client, teacher_space_id, "Course")


@pytest.mark.parametrize("method", ["post", "get", "patch", "delete"])
def test_section_endpoints_require_authentication(client: TestClient, method: str) -> None:
    base = sections_path(
        "00000000-0000-0000-0000-000000000000",
        "00000000-0000-0000-0000-000000000000",
    )
    path = base if method in {"post", "get"} else f"{base}/00000000-0000-0000-0000-000000000000"
    response = client.request(
        method,
        path,
        json={"title": "Section", "position": 0} if method in {"post", "patch"} else None,
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 401


def test_create_list_get_update_and_delete_section(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    created = create_section(client, teacher_space_id, course_id, "Introduction", 0)
    assert created.status_code == 201
    assert created.json()["course_id"] == course_id

    base = sections_path(teacher_space_id, course_id)
    listed = client.get(base)
    assert listed.status_code == 200
    assert [section["id"] for section in listed.json()] == [created.json()["id"]]
    item = f"{base}/{created.json()['id']}"
    assert client.get(item).json()["title"] == "Introduction"

    renamed = client.patch(item, json={"title": "Updated"}, headers=MUTATION_HEADERS)
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Updated"
    assert renamed.json()["position"] == 0
    moved = client.patch(item, json={"position": 4}, headers=MUTATION_HEADERS)
    assert moved.status_code == 200
    assert moved.json()["title"] == "Updated"
    assert moved.json()["position"] == 4

    assert client.delete(item, headers=MUTATION_HEADERS).status_code == 204
    assert client.get(item).status_code == 404


def test_list_is_ordered_by_position_then_id(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    last = create_section(client, teacher_space_id, course_id, "Last", 2).json()
    tied_b = create_section(client, teacher_space_id, course_id, "Tied B", 0).json()
    tied_a = create_section(client, teacher_space_id, course_id, "Tied A", 0).json()

    tied = sorted([tied_a, tied_b], key=lambda section: section["id"])
    listed = client.get(sections_path(teacher_space_id, course_id)).json()
    assert [section["id"] for section in listed] == [tied[0]["id"], tied[1]["id"], last["id"]]


def test_existing_empty_course_returns_empty_list(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    assert client.get(sections_path(teacher_space_id, course_id)).json() == []


def test_non_owner_cannot_access_sections(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    section = create_section(client, teacher_space_id, course_id, "Private", 0).json()
    authenticate(client, "other@example.com")

    base = sections_path(teacher_space_id, course_id)
    assert client.get(base).status_code == 404
    assert client.get(f"{base}/{section['id']}").status_code == 404
    assert create_section(client, teacher_space_id, course_id, "Stolen", 0).status_code == 404
    assert client.patch(
        f"{base}/{section['id']}", json={"title": "Stolen"}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert client.delete(f"{base}/{section['id']}", headers=MUTATION_HEADERS).status_code == 404


def test_cross_environment_and_cross_course_access_returns_404(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    first_space, first_course = setup_course(client, "First Space")
    section = create_section(client, first_space, first_course, "Private", 0).json()

    second_space, second_course = setup_course(client, "Second Space")
    cross_environment = f"{sections_path(second_space, second_course)}/{section['id']}"
    assert client.get(cross_environment).status_code == 404

    another_course = create_course(client, first_space, "Another Course")
    cross_course = f"{sections_path(first_space, another_course)}/{section['id']}"
    assert client.get(cross_course).status_code == 404
    assert client.patch(
        cross_course, json={"position": 1}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert client.delete(cross_course, headers=MUTATION_HEADERS).status_code == 404


def test_missing_section_returns_404_for_item_operations(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    item = f"{sections_path(teacher_space_id, course_id)}/00000000-0000-0000-0000-000000000000"
    assert client.get(item).status_code == 404
    assert client.patch(
        item, json={"title": "Missing"}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert client.delete(item, headers=MUTATION_HEADERS).status_code == 404


def test_create_requires_existing_environment_and_course(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "No Environment")
    missing_course = "00000000-0000-0000-0000-000000000000"
    assert create_section(client, teacher_space_id, missing_course, "Missing", 0).status_code == 404

    create_environment(client, teacher_space_id)
    assert create_section(client, teacher_space_id, missing_course, "Missing", 0).status_code == 404


def test_validation_and_client_controlled_relationship_are_rejected(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    base = sections_path(teacher_space_id, course_id)
    assert create_section(client, teacher_space_id, course_id, "   ", 0).status_code == 422
    assert create_section(client, teacher_space_id, course_id, "x" * 121, 0).status_code == 422
    assert create_section(client, teacher_space_id, course_id, "Negative", -1).status_code == 422
    assert client.post(
        base,
        json={"title": "Section", "position": 0, "owner_id": "forbidden"},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    section = create_section(client, teacher_space_id, course_id, "Section", 0).json()
    item = f"{base}/{section['id']}"
    assert client.patch(item, json={}, headers=MUTATION_HEADERS).status_code == 422
    assert client.patch(
        item,
        json={"course_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    ).status_code == 422


def test_disabled_teacher_space_sections_are_read_only(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id, course_id = setup_course(client)
    section = create_section(client, teacher_space_id, course_id, "Readable", 0).json()
    assert client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/disable", headers=MUTATION_HEADERS
    ).status_code == 200

    base = sections_path(teacher_space_id, course_id)
    item = f"{base}/{section['id']}"
    assert client.get(base).status_code == 200
    assert client.get(item).status_code == 200
    assert create_section(client, teacher_space_id, course_id, "Forbidden", 1).status_code == 409
    assert client.patch(
        item, json={"title": "Forbidden"}, headers=MUTATION_HEADERS
    ).status_code == 409
    assert client.delete(item, headers=MUTATION_HEADERS).status_code == 409


def test_openapi_contains_section_contract_including_delete(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    collection = (
        "/api/v1/teacher-spaces/{teacher_space_id}/environment"
        "/courses/{course_id}/sections"
    )
    item = f"{collection}/{{section_id}}"
    assert {"post", "get"} <= paths[collection].keys()
    assert {"get", "patch", "delete"} <= paths[item].keys()
