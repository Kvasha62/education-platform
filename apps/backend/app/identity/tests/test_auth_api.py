from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.identity.infrastructure.models import AuthSessionModel
from app.main import app

engine = create_engine(
    "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
TEST_ORIGIN = "http://frontend.test"


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


def register(client: TestClient, email: str = "person@example.com"):
    return client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a secure password"}
    )


def login(client: TestClient, password: str = "a secure password"):
    return client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": password}
    )


def assert_no_credentials(payload) -> None:
    serialized = str(payload).casefold()
    assert "password" not in serialized
    assert "password_hash" not in serialized


def test_registration_success_and_safe_response(client: TestClient) -> None:
    response = register(client, "Person@Example.COM")
    assert response.status_code == 201
    assert response.json()["email"] == "person@example.com"
    assert_no_credentials(response.json())


def test_duplicate_registration(client: TestClient) -> None:
    assert register(client).status_code == 201
    response = register(client, "PERSON@example.com")
    assert response.status_code == 409
    assert_no_credentials(response.json())


def test_login_success_and_failure(client: TestClient) -> None:
    register(client)
    failed = login(client, "wrong password")
    assert failed.status_code == 401
    assert failed.json() == {"detail": "Invalid email or password"}

    response = login(client)
    assert response.status_code == 200
    assert "education_session" in response.cookies
    assert_no_credentials(response.json())


def test_me_requires_authentication_and_returns_identity(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    register(client)
    login(client)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "person@example.com"
    assert_no_credentials(response.json())


def assert_successful_logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout", headers={"Origin": TEST_ORIGIN})
    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}
    assert "education_session=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_revokes_session_and_is_idempotent(client: TestClient) -> None:
    register(client)
    login(client)
    token = client.cookies.get("education_session")
    assert token

    missing_origin = client.post("/api/v1/auth/logout")
    assert missing_origin.status_code == 403

    assert_successful_logout(client)
    client.cookies.set("education_session", token)
    assert client.get("/api/v1/auth/me").status_code == 401

    # An explicitly revoked session is still a successful logout.
    assert_successful_logout(client)
    # The previous response clears the cookie, so this is a repeated logout with no session.
    assert_successful_logout(client)


def test_logout_without_session_succeeds_and_clears_cookie(client: TestClient) -> None:
    assert_successful_logout(client)


def test_logout_with_expired_session_succeeds_and_clears_cookie(client: TestClient) -> None:
    register(client)
    login(client)
    with TestingSession.begin() as session:
        session.execute(
            update(AuthSessionModel).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert client.get("/api/v1/auth/me").status_code == 401
    assert_successful_logout(client)


def test_openapi_contains_authentication_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
    } <= paths.keys()
