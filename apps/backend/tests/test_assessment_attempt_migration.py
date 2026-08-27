import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, select
from sqlalchemy.pool import StaticPool

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260827_0018_rename_assessment_attempt_submission.py"
)


def load_migration() -> dict[str, Any]:
    return cast(dict[str, Any], runpy.run_path(str(MIGRATION_PATH)))


def test_submission_column_rename_preserves_existing_values(monkeypatch):
    metadata = MetaData()
    attempts = Table(
        "assessment_attempts",
        metadata,
        Column("id", String, primary_key=True),
        Column("submission_data", String, nullable=True),
    )
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    migration = load_migration()

    with engine.begin() as connection:
        connection.execute(
            attempts.insert(),
            [
                {"id": "attempt-1", "submission_data": None},
                {"id": "attempt-2", "submission_data": "existing answer"},
                {"id": "attempt-3", "submission_data": "   "},
            ],
        )
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration["op"], "alter_column", operations.alter_column)
        upgrade = cast(Callable[[], None], migration["upgrade"])

        upgrade()

        columns = {column["name"] for column in inspect(connection).get_columns(attempts.name)}
        rows = connection.execute(
            select(
                Table("assessment_attempts", MetaData(), autoload_with=connection)
            ).order_by(attempts.c.id)
        ).mappings().all()

    assert columns == {"id", "submission"}
    assert [dict(row) for row in rows] == [
        {"id": "attempt-1", "submission": None},
        {"id": "attempt-2", "submission": "existing answer"},
        {"id": "attempt-3", "submission": "   "},
    ]
