"""Architecture guards for the Education / Content bounded-context boundary."""

import ast
from pathlib import Path

from app.content.infrastructure import models as content_models  # noqa: F401
from app.content.public import ContentLookup
from app.core.database import Base
from app.education.infrastructure import models as education_models  # noqa: F401
from app.identity.infrastructure import models as identity_models  # noqa: F401

EDUCATION_ENTITY_TABLES = {
    "educational_environments",
    "courses",
    "sections",
    "learning_units",
    "activities",
}
EDUCATION_TABLES = EDUCATION_ENTITY_TABLES | {"activity_content_links"}
EDUCATION_AND_TEACHER_TABLES = EDUCATION_TABLES | {"teacher_spaces"}
EDUCATION_COLUMNS = {
    "educational_environments": {"id", "teacher_space_id", "name", "created_at", "updated_at"},
    "courses": {"id", "educational_environment_id", "title", "created_at", "updated_at"},
    "sections": {"id", "course_id", "title", "position", "created_at", "updated_at"},
    "learning_units": {"id", "section_id", "title", "position", "created_at", "updated_at"},
    "activities": {
        "id",
        "learning_unit_id",
        "title",
        "type",
        "position",
        "created_at",
        "updated_at",
    },
    "activity_content_links": {"activity_id", "content_id"},
}


def _imports(package: Path) -> set[str]:
    imports: set[str] = set()
    for source in package.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports


def test_education_persistence_remains_decoupled_from_content() -> None:
    education_tables = {
        name: table for name, table in Base.metadata.tables.items() if name in EDUCATION_TABLES
    }
    assert education_tables.keys() == EDUCATION_TABLES

    for name, table in education_tables.items():
        assert set(table.c.keys()) == EDUCATION_COLUMNS[name]
        if name in EDUCATION_ENTITY_TABLES:
            assert all("content" not in column.name.casefold() for column in table.columns)
        assert all(
            foreign_key.column.table.name in EDUCATION_TABLES for foreign_key in table.foreign_keys
        )


def test_content_owns_separate_user_owned_persistence() -> None:
    content_table = Base.metadata.tables["contents"]

    assert set(content_table.c.keys()) == {
        "id",
        "owner_user_id",
        "type",
        "title",
        "status",
        "created_at",
        "updated_at",
    }
    assert {foreign_key.target_fullname for foreign_key in content_table.foreign_keys} == {
        "identities.id"
    }
    assert all(
        foreign_key.column.table.name not in EDUCATION_AND_TEACHER_TABLES
        for foreign_key in content_table.foreign_keys
    )


def test_runtime_dependency_uses_only_content_public_interface() -> None:
    backend = Path(__file__).parents[1] / "app"
    education_imports = _imports(backend / "education")
    content_imports = _imports(backend / "content")

    content_dependencies = {name for name in education_imports if name.startswith("app.content")}
    assert content_dependencies == {"app.content.public"}
    assert not {name for name in content_imports if name.startswith("app.education")}


def test_activity_persistence_boundary_is_learning_unit_only() -> None:
    activity_table = Base.metadata.tables["activities"]
    assert {foreign_key.target_fullname for foreign_key in activity_table.foreign_keys} == {
        "learning_units.id"
    }


def test_activity_content_association_contract() -> None:
    link_table = Base.metadata.tables["activity_content_links"]
    assert [column.name for column in link_table.primary_key.columns] == [
        "activity_id",
        "content_id",
    ]
    assert {foreign_key.target_fullname for foreign_key in link_table.foreign_keys} == {
        "activities.id"
    }
    activity_fk = next(iter(link_table.foreign_keys))
    assert activity_fk.ondelete == "CASCADE"
    assert not link_table.c.content_id.nullable
    assert not link_table.c.content_id.foreign_keys
    assert any(
        [column.name for column in index.columns] == ["content_id"] for index in link_table.indexes
    )


def test_content_public_interface_is_read_only() -> None:
    methods = {
        name
        for name, member in ContentLookup.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    assert methods == {"lookup_owned"}
