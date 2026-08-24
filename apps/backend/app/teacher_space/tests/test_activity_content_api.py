from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.content.api.dependencies import get_content_lookup
from app.content.public import ContentLookupUnavailable
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


def setup_activity(client: TestClient, name: str = "Space") -> tuple[str, str, str, str, str]:
    space = client.post("/api/v1/teacher-spaces", json={"name": name}, headers=HEADERS).json()
    environment = f"/api/v1/teacher-spaces/{space['id']}/environment"
    assert (
        client.post(environment, json={"name": "Environment"}, headers=HEADERS).status_code == 201
    )
    course = client.post(f"{environment}/courses", json={"title": "Course"}, headers=HEADERS).json()
    sections = f"{environment}/courses/{course['id']}/sections"
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
    return space["id"], course["id"], section["id"], unit["id"], activity["id"]


def links_path(values: tuple[str, str, str, str, str]) -> str:
    space, course, section, unit, activity = values
    return (
        f"/api/v1/teacher-spaces/{space}/environment/courses/{course}"
        f"/sections/{section}/units/{unit}/activities/{activity}/contents"
    )


def create_content(client: TestClient, title: str, publish: bool = False) -> dict:
    content = client.post(
        "/api/v1/contents",
        json={"title": title, "type": "article"},
        headers=HEADERS,
    ).json()
    if publish:
        content = client.post(f"/api/v1/contents/{content['id']}/publish", headers=HEADERS).json()
    return content


@pytest.mark.parametrize("method", ["post", "get", "delete"])
def test_authentication_required(client: TestClient, method: str) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    base = links_path((missing, missing, missing, missing, missing))
    path = base if method != "delete" else f"{base}/{missing}"
    response = client.request(method, path, json={"content_id": missing}, headers=HEADERS)
    assert response.status_code == 401


def test_owner_attach_list_detach_lifecycle(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup_activity(client)
    base = links_path(values)
    draft = create_content(client, "Draft")
    published = create_content(client, "Published", publish=True)

    first = client.post(base, json={"content_id": draft["id"]}, headers=HEADERS)
    repeated = client.post(base, json={"content_id": draft["id"]}, headers=HEADERS)
    assert first.status_code == repeated.status_code == 200
    assert (
        first.json()
        == repeated.json()
        == {
            "activity_id": values[-1],
            "content_id": draft["id"],
        }
    )
    assert (
        client.post(base, json={"content_id": published["id"]}, headers=HEADERS).status_code == 200
    )

    listed = client.get(base)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == sorted([draft["id"], published["id"]])
    by_id = {item["id"]: item for item in listed.json()}
    assert by_id[draft["id"]] == {
        "id": draft["id"],
        "type": "article",
        "status": "draft",
        "available_for_student": False,
    }
    assert by_id[published["id"]]["available_for_student"] is True
    assert all(
        set(item) == {"id", "type", "status", "available_for_student"} for item in listed.json()
    )

    detach = f"{base}/{draft['id']}"
    assert client.delete(detach, headers=HEADERS).status_code == 204
    assert client.delete(detach, headers=HEADERS).status_code == 204
    assert [item["id"] for item in client.get(base).json()] == [published["id"]]


def test_missing_and_cross_owner_content_attach_are_indistinguishable(client: TestClient) -> None:
    owner_token = auth(client, "owner@example.com")
    base = links_path(setup_activity(client))
    owned = create_content(client, "Owner Content")

    auth(client, "other@example.com")
    other_content = create_content(client, "Other Content")
    use(client, owner_token)

    missing_response = client.post(
        base,
        json={"content_id": "00000000-0000-0000-0000-000000000000"},
        headers=HEADERS,
    )
    cross_owner_response = client.post(
        base, json={"content_id": other_content["id"]}, headers=HEADERS
    )
    assert missing_response.status_code == cross_owner_response.status_code == 404
    assert missing_response.json() == cross_owner_response.json()
    assert client.post(base, json={"content_id": owned["id"]}, headers=HEADERS).status_code == 200


def test_complete_nested_scope_isolation(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup_activity(client, "First")
    content = create_content(client, "Content")
    base = links_path(values)
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 200

    other = setup_activity(client, "Second")
    for index in range(5):
        altered = list(values)
        altered[index] = other[index]
        assert client.get(links_path(tuple(altered))).status_code == 404  # type: ignore[arg-type]

    auth(client, "other@example.com")
    assert client.get(base).status_code == 404
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 404


def test_stale_content_has_safe_unavailable_representation(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = links_path(setup_activity(client))
    content = create_content(client, "Temporary")
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 200
    assert client.delete(f"/api/v1/contents/{content['id']}", headers=HEADERS).status_code == 204

    assert client.get(base).json() == [
        {
            "id": content["id"],
            "type": None,
            "status": None,
            "available_for_student": False,
        }
    ]


class FailingLookup:
    def lookup_owned(self, content_id: UUID, owner_user_id: UUID):
        raise ContentLookupUnavailable


def test_content_lookup_failure_maps_to_503(client: TestClient) -> None:
    auth(client, "owner@example.com")
    base = links_path(setup_activity(client))
    content = create_content(client, "Content")
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 200

    app.dependency_overrides[get_content_lookup] = FailingLookup
    try:
        assert client.get(base).status_code == 503
        assert (
            client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code
            == 503
        )
    finally:
        app.dependency_overrides.pop(get_content_lookup, None)


def test_csrf_validation_and_disabled_space_policy(client: TestClient) -> None:
    auth(client, "owner@example.com")
    values = setup_activity(client)
    base = links_path(values)
    content = create_content(client, "Content")

    assert (
        client.post(
            base,
            json={"content_id": content["id"]},
            headers={"Origin": "https://evil.test"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            base,
            json={"content_id": content["id"], "extra": True},
            headers=HEADERS,
        ).status_code
        == 422
    )
    assert client.post(base, json={"content_id": "bad"}, headers=HEADERS).status_code == 422
    assert client.delete(f"{base}/bad", headers=HEADERS).status_code == 422
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 200
    assert (
        client.delete(
            f"{base}/{content['id']}", headers={"Origin": "https://evil.test"}
        ).status_code
        == 403
    )

    assert (
        client.post(f"/api/v1/teacher-spaces/{values[0]}/disable", headers=HEADERS).status_code
        == 200
    )
    assert client.get(base).status_code == 200
    assert client.post(base, json={"content_id": content["id"]}, headers=HEADERS).status_code == 409
    assert client.delete(f"{base}/{content['id']}", headers=HEADERS).status_code == 409


def test_openapi_contract_and_existing_content_contract(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    collection = (
        "/api/v1/teacher-spaces/{teacher_space_id}/environment/courses/{course_id}"
        "/sections/{section_id}/units/{unit_id}/activities/{activity_id}/contents"
    )
    assert {"post", "get"} <= paths[collection].keys()
    assert "delete" in paths[f"{collection}/{{content_id}}"]
    assert {"post", "get"} <= paths["/api/v1/contents"].keys()
    assert {"get", "patch", "delete"} <= paths["/api/v1/contents/{content_id}"].keys()
