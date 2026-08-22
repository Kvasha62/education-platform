from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_db
from app.identity.api.rate_limit import login_limiter, register_limiter
from app.main import app

engine = create_engine(
    "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
TRUSTED_ORIGIN = "http://localhost:5173"
TRUSTED_HEADERS = {"Origin": TRUSTED_ORIGIN}


def override_db() -> Generator[Session, None, None]:
    with TestingSession() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def security_settings(
    *, login_limit: int = 100, register_limit: int = 100, secure: bool = False
) -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite://",
        minio_endpoint="http://minio.test",
        frontend_origin=TRUSTED_ORIGIN,
        auth_cookie_secure=secure,
        auth_session_ttl_seconds=3600,
        auth_login_rate_limit=login_limit,
        auth_register_rate_limit=register_limit,
        auth_rate_limit_window_seconds=60,
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    login_limiter.reset()
    register_limiter.reset()
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = security_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    login_limiter.reset()
    register_limiter.reset()


def register(client: TestClient, email: str = "person@example.com"):
    return client.post(
        "/api/v1/auth/register", json={"email": email, "password": "a secure password"}
    )


def login(client: TestClient, email: str = "person@example.com"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong password"},
        headers=TRUSTED_HEADERS,
    )


def test_login_rate_limit_returns_429_with_retry_after(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: security_settings(login_limit=2)
    assert login(client).status_code == 401
    assert login(client).status_code == 401
    blocked = login(client)
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "Too many requests"}
    assert int(blocked.headers["Retry-After"]) > 0


def test_register_rate_limit_returns_429_with_retry_after(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: security_settings(register_limit=2)
    assert register(client, "one@example.com").status_code == 201
    assert register(client, "two@example.com").status_code == 201
    blocked = register(client, "three@example.com")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_secure_cookie_can_be_enabled_without_changing_session_contract(
    client: TestClient,
) -> None:
    app.dependency_overrides[get_settings] = lambda: security_settings(secure=True)
    assert register(client).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "a secure password"},
        headers=TRUSTED_HEADERS,
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie


def test_all_cookie_authenticated_mutations_reject_untrusted_origin(
    client: TestClient,
) -> None:
    assert register(client).status_code == 201
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "a secure password"},
        headers=TRUSTED_HEADERS,
    ).status_code == 200
    teacher = client.post(
        "/api/v1/teacher-spaces", json={"name": "Space"}, headers=TRUSTED_HEADERS
    ).json()
    environment_path = f"/api/v1/teacher-spaces/{teacher['id']}/environment"
    assert client.post(
        environment_path, json={"name": "Environment"}, headers=TRUSTED_HEADERS
    ).status_code == 201
    courses_path = f"{environment_path}/courses"
    course = client.post(
        courses_path, json={"title": "Course"}, headers=TRUSTED_HEADERS
    ).json()
    sections_path = f"{courses_path}/{course['id']}/sections"
    section = client.post(
        sections_path,
        json={"title": "Section", "position": 0},
        headers=TRUSTED_HEADERS,
    ).json()
    units_path = f"{sections_path}/{section['id']}/units"
    unit = client.post(
        units_path,
        json={"title": "Unit", "position": 0},
        headers=TRUSTED_HEADERS,
    ).json()
    activities_path = f"{units_path}/{unit['id']}/activities"
    activity = client.post(
        activities_path,
        json={"title": "Activity", "type": "lecture", "position": 0},
        headers=TRUSTED_HEADERS,
    ).json()

    cases = [
        ("post", "/api/v1/auth/logout", None),
        ("post", "/api/v1/teacher-spaces", {"name": "Another"}),
        ("patch", f"/api/v1/teacher-spaces/{teacher['id']}", {"name": "Changed"}),
        ("post", f"/api/v1/teacher-spaces/{teacher['id']}/disable", None),
        ("post", environment_path, {"name": "Second"}),
        ("patch", environment_path, {"name": "Changed"}),
        ("post", courses_path, {"title": "Second"}),
        ("patch", f"{courses_path}/{course['id']}", {"title": "Changed"}),
        ("post", sections_path, {"title": "Second", "position": 1}),
        ("patch", f"{sections_path}/{section['id']}", {"title": "Changed"}),
        ("delete", f"{sections_path}/{section['id']}", None),
        ("post", units_path, {"title": "Second", "position": 1}),
        ("patch", f"{units_path}/{unit['id']}", {"title": "Changed"}),
        ("delete", f"{units_path}/{unit['id']}", None),
        ("post", activities_path, {"title": "Second", "type": "video", "position": 1}),
        ("patch", f"{activities_path}/{activity['id']}", {"title": "Changed"}),
        ("delete", f"{activities_path}/{activity['id']}", None),
    ]
    for method, path, payload in cases:
        response = client.request(method, path, json=payload, headers={"Origin": "https://evil.test"})
        assert response.status_code == 403, (method, path, response.text)


def test_cors_allows_configured_frontend_with_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == TRUSTED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "content-type" in response.headers["access-control-allow-headers"].casefold()

    delete_response = client.options(
        "/api/v1/teacher-spaces/id/environment/courses/id/sections/id",
        headers={
            "Origin": TRUSTED_ORIGIN,
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert delete_response.status_code == 200
    assert delete_response.headers["access-control-allow-origin"] == TRUSTED_ORIGIN


def test_cors_does_not_allow_unknown_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "https://evil.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_cookie_defaults_secure_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    assert get_settings().auth_cookie_secure is True


def test_cookie_defaults_insecure_for_http_local_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    assert get_settings().auth_cookie_secure is False


def test_non_positive_session_ttl_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SESSION_TTL_SECONDS", "0")
    with pytest.raises(ValueError, match="AUTH_SESSION_TTL_SECONDS"):
        get_settings()
