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
    registration = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a secure password"}
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a secure password"}
    )
    assert login.status_code == 200
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return token


def use_session(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)


def create_space(client: TestClient, name: str):
    return client.post(
        "/api/v1/teacher-spaces", json={"name": name}, headers=MUTATION_HEADERS
    )


def test_create_requires_authentication(client: TestClient) -> None:
    response = create_space(client, "Mathematics")
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/v1/teacher-spaces", None),
        ("get", "/api/v1/teacher-spaces/00000000-0000-0000-0000-000000000000", None),
        (
            "patch",
            "/api/v1/teacher-spaces/00000000-0000-0000-0000-000000000000",
            {"name": "Updated"},
        ),
        (
            "post",
            "/api/v1/teacher-spaces/00000000-0000-0000-0000-000000000000/disable",
            None,
        ),
    ],
)
def test_all_other_endpoints_require_authentication(
    client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    response = client.request(method, path, json=body, headers=MUTATION_HEADERS)
    assert response.status_code == 401


def test_authenticated_user_can_own_multiple_spaces(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    first = create_space(client, "Mathematics")
    second = create_space(client, "Physics")
    assert first.status_code == second.status_code == 201
    assert first.json()["status"] == second.json()["status"] == "active"

    listed = client.get("/api/v1/teacher-spaces")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Mathematics", "Physics"]


def test_owner_and_status_are_not_client_controlled(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    create_response = client.post(
        "/api/v1/teacher-spaces",
        json={"name": "Space", "owner_user_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    )
    assert create_response.status_code == 422
    status_response = client.post(
        "/api/v1/teacher-spaces",
        json={"name": "Space", "status": "disabled"},
        headers=MUTATION_HEADERS,
    )
    assert status_response.status_code == 422


def test_list_and_get_expose_only_owned_spaces(client: TestClient) -> None:
    owner_token = authenticate(client, "owner@example.com")
    owned = create_space(client, "Owner Space").json()

    other_token = authenticate(client, "other@example.com")
    create_space(client, "Other Space")
    assert [item["name"] for item in client.get("/api/v1/teacher-spaces").json()] == [
        "Other Space"
    ]
    assert client.get(f"/api/v1/teacher-spaces/{owned['id']}").status_code == 404

    use_session(client, owner_token)
    response = client.get(f"/api/v1/teacher-spaces/{owned['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Owner Space"
    use_session(client, other_token)


def test_only_owner_can_update_name(client: TestClient) -> None:
    owner_token = authenticate(client, "owner@example.com")
    teacher_space = create_space(client, "Original").json()
    other_token = authenticate(client, "other@example.com")

    path = f"/api/v1/teacher-spaces/{teacher_space['id']}"
    denied = client.patch(
        path,
        json={"name": "Stolen"},
        headers=MUTATION_HEADERS,
    )
    assert denied.status_code == 404
    assert client.post(f"{path}/disable", headers=MUTATION_HEADERS).status_code == 404

    use_session(client, owner_token)
    updated = client.patch(
        f"/api/v1/teacher-spaces/{teacher_space['id']}",
        json={"name": "Updated"},
        headers=MUTATION_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated"
    use_session(client, other_token)


def test_update_rejects_invalid_or_arbitrary_fields(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space = create_space(client, "Original").json()
    path = f"/api/v1/teacher-spaces/{teacher_space['id']}"
    assert client.patch(path, json={"name": "   "}, headers=MUTATION_HEADERS).status_code == 422
    assert client.patch(
        path, json={"name": "Valid", "status": "disabled"}, headers=MUTATION_HEADERS
    ).status_code == 422


def test_disabled_space_is_visible_but_read_only(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space = create_space(client, "Space").json()
    path = f"/api/v1/teacher-spaces/{teacher_space['id']}"

    disabled = client.post(f"{path}/disable", headers=MUTATION_HEADERS)
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    assert client.get(path).json()["status"] == "disabled"
    assert client.get("/api/v1/teacher-spaces").json()[0]["status"] == "disabled"
    assert client.patch(
        path, json={"name": "No change"}, headers=MUTATION_HEADERS
    ).status_code == 409
    assert client.post(f"{path}/disable", headers=MUTATION_HEADERS).status_code == 409


def test_openapi_contains_teacher_space_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/v1/teacher-spaces",
        "/api/v1/teacher-spaces/{teacher_space_id}",
        "/api/v1/teacher-spaces/{teacher_space_id}/disable",
    } <= paths.keys()
