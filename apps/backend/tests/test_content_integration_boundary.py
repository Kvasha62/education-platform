"""Architecture guards for the Education / Content bounded-context boundary."""

from pathlib import Path

from app.content.infrastructure import models as content_models  # noqa: F401
from app.core.database import Base
from app.education.infrastructure import models as education_models  # noqa: F401

EDUCATION_TABLES = {
    "educational_environments",
    "courses",
    "sections",
    "learning_units",
    "activities",
}
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
}


def test_education_persistence_remains_decoupled_from_content() -> None:
    education_tables = {
        name: table for name, table in Base.metadata.tables.items() if name in EDUCATION_TABLES
    }
    assert education_tables.keys() == EDUCATION_TABLES

    for name, table in education_tables.items():
        assert set(table.c.keys()) == EDUCATION_COLUMNS[name]
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


def test_no_education_runtime_import_of_content() -> None:
    education_package = Path(__file__).parents[1] / "app" / "education"
    assert all(
        "app.content" not in source.read_text(encoding="utf-8")
        for source in education_package.rglob("*.py")
    )


def test_activity_persistence_boundary_is_learning_unit_only() -> None:
    activity_table = Base.metadata.tables["activities"]

    assert all("content" not in column.name.casefold() for column in activity_table.columns)
    assert {foreign_key.target_fullname for foreign_key in activity_table.foreign_keys} == {
        "learning_units.id"
    }
