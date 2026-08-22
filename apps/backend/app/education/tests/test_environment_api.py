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


def create_teacher_space(client: TestClient, name: str = "Teacher Space") -> str:
    response = client.post(
        "/api/v1/teacher-spaces", json={"name": name}, headers=MUTATION_HEADERS
    )
    assert response.status_code == 201
    return response.json()["id"]


def environment_path(teacher_space_id: str) -> str:
    return f"/api/v1/teacher-spaces/{teacher_space_id}/environment"


def create_environment(client: TestClient, teacher_space_id: str, name: str = "Environment"):
    return client.post(
        environment_path(teacher_space_id), json={"name": name}, headers=MUTATION_HEADERS
    )


@pytest.mark.parametrize("method", ["post", "get", "patch"])
def test_environment_endpoints_require_authentication(
    client: TestClient, method: str
) -> None:
    path = environment_path("00000000-0000-0000-0000-000000000000")
    response = client.request(
        method,
        path,
        json={"name": "Environment"} if method != "get" else None,
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 401


def test_owner_can_create_get_and_update_environment(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client)

    created = create_environment(client, teacher_space_id, "  Learning World  ")
    assert created.status_code == 201
    assert created.json()["teacher_space_id"] == teacher_space_id
    assert created.json()["name"] == "Learning World"

    retrieved = client.get(environment_path(teacher_space_id))
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == created.json()["id"]

    updated = client.patch(
        environment_path(teacher_space_id),
        json={"name": "Updated World"},
        headers=MUTATION_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated World"
    assert updated.json()["teacher_space_id"] == teacher_space_id


def test_second_environment_is_rejected(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client)
    assert create_environment(client, teacher_space_id, "First").status_code == 201
    response = create_environment(client, teacher_space_id, "Second")
    assert response.status_code == 409


def test_non_owner_cannot_access_environment(client: TestClient) -> None:
    owner_token = authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client)
    create_environment(client, teacher_space_id)

    authenticate(client, "other@example.com")
    path = environment_path(teacher_space_id)
    assert client.get(path).status_code == 404
    assert client.patch(
        path, json={"name": "Stolen"}, headers=MUTATION_HEADERS
    ).status_code == 404
    assert create_environment(client, teacher_space_id, "Stolen").status_code == 404
    use_session(client, owner_token)


def test_client_cannot_control_ownership_or_teacher_space_id(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client)
    path = environment_path(teacher_space_id)
    assert client.post(
        path,
        json={"name": "Environment", "owner_user_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    assert client.post(
        path,
        json={"name": "Environment", "teacher_space_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    assert client.post(
        path,
        json={"name": "Environment", "status": "active"},
        headers=MUTATION_HEADERS,
    ).status_code == 422
    assert create_environment(client, teacher_space_id).status_code == 201
    assert client.patch(
        path,
        json={"name": "Updated", "teacher_space_id": "00000000-0000-0000-0000-000000000000"},
        headers=MUTATION_HEADERS,
    ).status_code == 422


def test_invalid_name_is_rejected(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client)
    assert create_environment(client, teacher_space_id, "   ").status_code == 422
    assert create_environment(client, teacher_space_id, "x" * 121).status_code == 422


def test_disabled_teacher_space_environment_is_read_only(client: TestClient) -> None:
    authenticate(client, "owner@example.com")
    teacher_space_id = create_teacher_space(client, "With Environment")
    assert create_environment(client, teacher_space_id).status_code == 201
    assert client.post(
        f"/api/v1/teacher-spaces/{teacher_space_id}/disable", headers=MUTATION_HEADERS
    ).status_code == 200

    path = environment_path(teacher_space_id)
    assert client.get(path).status_code == 200
    assert client.patch(
        path, json={"name": "No change"}, headers=MUTATION_HEADERS
    ).status_code == 409

    second_space_id = create_teacher_space(client, "Without Environment")
    assert client.post(
        f"/api/v1/teacher-spaces/{second_space_id}/disable", headers=MUTATION_HEADERS
    ).status_code == 200
    assert create_environment(client, second_space_id).status_code == 409


def test_openapi_contains_environment_contract(client: TestClient) -> None:
    path = "/api/v1/teacher-spaces/{teacher_space_id}/environment"
    operation = client.get("/openapi.json").json()["paths"][path]
    assert {"post", "get", "patch"} <= operation.keys()
