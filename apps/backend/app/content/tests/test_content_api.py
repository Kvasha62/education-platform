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


def use(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)


def create(client: TestClient, title: str = "Content", kind: str = "article"):
    return client.post("/api/v1/contents", json={"title": title, "type": kind}, headers=HEADERS)


@pytest.mark.parametrize("method", ["post", "get", "patch", "delete"])
def test_authentication_required(client: TestClient, method: str) -> None:
    path = (
        "/api/v1/contents"
        if method in {"post", "get"}
        else "/api/v1/contents/00000000-0000-0000-0000-000000000000"
    )
    response = client.request(method, path, json={"title": "X", "type": "article"}, headers=HEADERS)
    assert response.status_code == 401


def test_owner_crud_and_default_contract(client: TestClient) -> None:
    auth(client, "owner@example.com")
    first = create(client, "Article", "article")
    second = create(client, "Resource", "resource")
    assert first.status_code == second.status_code == 201
    assert first.json()["status"] == "draft"
    assert "owner_user_id" not in first.json()
    listed = client.get("/api/v1/contents").json()
    assert len(listed) == 2
    item = f"/api/v1/contents/{first.json()['id']}"
    assert client.get(item).status_code == 200
    changed = client.patch(item, json={"title": "Changed"}, headers=HEADERS)
    assert (changed.json()["title"], changed.json()["type"], changed.json()["status"]) == (
        "Changed",
        "article",
        "draft",
    )
    assert client.delete(item, headers=HEADERS).status_code == 204
    assert client.get(item).status_code == 404


def test_publish_is_owner_scoped_and_idempotent(client: TestClient) -> None:
    first_token = auth(client, "owner@example.com")
    content = create(client, "Publishable").json()
    publish_path = f"/api/v1/contents/{content['id']}/publish"

    first = client.post(publish_path, headers=HEADERS)
    repeated = client.post(publish_path, headers=HEADERS)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["status"] == repeated.json()["status"] == "published"
    assert first.json()["updated_at"].removesuffix("Z") == repeated.json()[
        "updated_at"
    ].removesuffix("Z")

    auth(client, "other@example.com")
    assert client.post(publish_path, headers=HEADERS).status_code == 404
    use(client, first_token)


def test_publish_requires_authentication_and_csrf(client: TestClient) -> None:
    missing = "/api/v1/contents/00000000-0000-0000-0000-000000000000/publish"
    assert client.post(missing, headers=HEADERS).status_code == 401

    auth(client, "owner@example.com")
    content = create(client).json()
    publish_path = f"/api/v1/contents/{content['id']}/publish"
    assert client.post(publish_path, headers={"Origin": "https://evil.test"}).status_code == 403


def test_cross_owner_isolation_and_owned_list(client: TestClient) -> None:
    first_token = auth(client, "first@example.com")
    private = create(client, "Private").json()
    auth(client, "second@example.com")
    own = create(client, "Own").json()
    assert [item["id"] for item in client.get("/api/v1/contents").json()] == [own["id"]]
    path = f"/api/v1/contents/{private['id']}"
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"title": "Stolen"}, headers=HEADERS).status_code == 404
    assert client.delete(path, headers=HEADERS).status_code == 404
    use(client, first_token)


def test_mass_assignment_and_immutable_fields_rejected(client: TestClient) -> None:
    auth(client, "owner@example.com")
    for extra in ({"owner_user_id": "x"}, {"status": "published"}, {"id": "x"}, {"unknown": 1}):
        assert (
            client.post(
                "/api/v1/contents", json={"title": "X", "type": "article", **extra}, headers=HEADERS
            ).status_code
            == 422
        )
    item = f"/api/v1/contents/{create(client).json()['id']}"
    for payload in (
        {},
        {"title": None},
        {"type": "resource"},
        {"status": "published"},
        {"owner_user_id": "x"},
        {"unknown": 1},
    ):
        assert client.patch(item, json=payload, headers=HEADERS).status_code == 422


def test_validation_nonexistent_and_csrf(client: TestClient) -> None:
    auth(client, "owner@example.com")
    assert create(client, " ").status_code == 422
    assert create(client, "x" * 121).status_code == 422
    assert create(client, kind="video").status_code == 422
    missing = "/api/v1/contents/00000000-0000-0000-0000-000000000000"
    assert client.get(missing).status_code == 404
    assert client.patch(missing, json={"title": "X"}, headers=HEADERS).status_code == 404
    assert client.delete(missing, headers=HEADERS).status_code == 404
    item = f"/api/v1/contents/{create(client).json()['id']}"
    for method, path, body in (
        ("post", "/api/v1/contents", {"title": "X", "type": "article"}),
        ("patch", item, {"title": "X"}),
        ("delete", item, None),
    ):
        assert (
            client.request(
                method, path, json=body, headers={"Origin": "https://evil.test"}
            ).status_code
            == 403
        )


def test_openapi_content_lifecycle_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"post", "get"} <= paths["/api/v1/contents"].keys()
    assert {"get", "patch", "delete"} <= paths["/api/v1/contents/{content_id}"].keys()
    assert "post" in paths["/api/v1/contents/{content_id}/publish"]
    assert all("attachment" not in path for path in paths if "content" in path)
