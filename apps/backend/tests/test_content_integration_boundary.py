"""Architecture guards for the approved Education / future Content boundary."""

from pathlib import Path

from app.core.database import Base
from app.education.infrastructure import models as education_models  # noqa: F401
from app.main import app

EDUCATION_TABLES = {
    "educational_environments",
    "courses",
    "sections",
    "learning_units",
}


def test_education_persistence_has_no_content_coupling() -> None:
    education_tables = {
        name: table
        for name, table in Base.metadata.tables.items()
        if name in EDUCATION_TABLES
    }
    assert education_tables.keys() == EDUCATION_TABLES

    for table in education_tables.values():
        assert all("content" not in column.name.casefold() for column in table.columns)
        assert all(
            foreign_key.column.table.name in EDUCATION_TABLES
            for foreign_key in table.foreign_keys
        )


def test_no_content_persistence_migration_exists() -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    assert all(
        "content" not in migration.read_text(encoding="utf-8").casefold()
        for migration in versions.glob("*.py")
    )


def test_no_content_api_is_exposed() -> None:
    assert all("/content" not in path.casefold() for path in app.openapi()["paths"])
