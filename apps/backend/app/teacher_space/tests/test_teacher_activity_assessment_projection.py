"""Teacher Activity Assessment Entry projection tests (ADR-0013)."""

import ast
from collections.abc import Generator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.composition import get_assessment_definition_id_lookup
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


def create(client: TestClient, base: str, title: str = "Activity", position: int = 0) -> dict:
    response = client.post(
        base,
        json={"title": title, "type": "lecture", "position": position},
        headers=HEADERS,
    )
    assert response.status_code == 201
    return response.json()


class RecordingLookup:
    def __init__(self, mapping: dict[UUID, UUID] | None = None) -> None:
        self.mapping = mapping or {}
        self.calls: list[UUID] = []

    def get_id_for_activity(self, activity_id: UUID) -> UUID | None:
        self.calls.append(activity_id)
        return self.mapping.get(activity_id)


def override_lookup(lookup: RecordingLookup) -> None:
    app.dependency_overrides[get_assessment_definition_id_lookup] = lambda: lookup


def test_teacher_activity_projection_exposes_assessment_definition_id(
    client: TestClient,
) -> None:
    auth(client, "owner@example.com")
    lookup = RecordingLookup()
    override_lookup(lookup)
    base = path(setup(client))
    assessed_id = create(client, base, "Assessed", 0)["id"]
    plain_id = create(client, base, "Plain", 1)["id"]

    definition_id = uuid4()
    lookup.mapping[UUID(assessed_id)] = definition_id

    items = client.get(base).json()
    assert isinstance(items, list)
    by_id = {item["id"]: item for item in items}
    assert by_id[assessed_id]["assessment_definition_id"] == str(definition_id)
    assert by_id[plain_id]["assessment_definition_id"] is None

    detail = client.get(f"{base}/{assessed_id}").json()
    assert detail["assessment_definition_id"] == str(definition_id)

    detail_plain = client.get(f"{base}/{plain_id}").json()
    assert detail_plain["assessment_definition_id"] is None


def test_teacher_activity_projection_uses_public_lookup_boundary(
    client: TestClient,
) -> None:
    auth(client, "owner@example.com")
    lookup = RecordingLookup()
    override_lookup(lookup)
    base = path(setup(client))
    created = create(client, base, "Assessed", 0)
    definition_id = uuid4()
    lookup.mapping[UUID(created["id"])] = definition_id

    items = client.get(base).json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]
    assert items[0]["assessment_definition_id"] == str(definition_id)
    assert lookup.calls, "Teacher Activity projection must query the public lookup boundary"
    assert UUID(created["id"]) in lookup.calls


def test_teacher_activity_projection_does_not_expose_assessment_internals(
    client: TestClient,
) -> None:
    auth(client, "owner@example.com")
    lookup = RecordingLookup()
    override_lookup(lookup)
    base = path(setup(client))
    activity = create(client, base, "Activity", 0)
    definition_id = uuid4()
    lookup.mapping[UUID(activity["id"])] = definition_id

    payload = client.get(f"{base}/{activity['id']}").json()
    assert set(payload) == {
        "id",
        "learning_unit_id",
        "title",
        "type",
        "position",
        "created_at",
        "updated_at",
        "assessment_definition_id",
    }
    assert not {"instructions", "status", "submission", "result", "feedback", "student_id"} & set(
        payload
    )
    assert payload["assessment_definition_id"] == str(definition_id)


def test_teacher_activity_projection_preserves_existing_crud_behavior(
    client: TestClient,
) -> None:
    auth(client, "owner@example.com")
    override_lookup(RecordingLookup())
    base = path(setup(client))
    created = create(client, base, "Activity", 0)
    assert created["assessment_definition_id"] is None

    updated = client.patch(
        f"{base}/{created['id']}",
        json={"title": "Changed"},
        headers=HEADERS,
    ).json()
    assert updated["title"] == "Changed"
    assert updated["assessment_definition_id"] is None

    deleted = client.delete(f"{base}/{created['id']}", headers=HEADERS)
    assert deleted.status_code == 204
    assert client.get(f"{base}/{created['id']}").status_code == 404


def test_teacher_activity_projection_code_does_not_import_assessment_persistence() -> None:
    module = Path(__file__).parents[1] / "api" / "activity_router.py"
    tree = ast.parse(module.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not {name for name in imports if name.startswith("app.assessment.infrastructure")}
    assert "app.assessment.application.definition_lookup" in imports
