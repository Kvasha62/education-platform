import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import Column, MetaData, String, Table, create_engine, insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.pool import StaticPool

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260827_0017_add_assessment_result_semantics.py"
)


def load_migration() -> dict[str, Any]:
    return cast(dict[str, Any], runpy.run_path(str(MIGRATION_PATH)))


def foundation_result_table(metadata: MetaData) -> Table:
    return Table(
        "assessment_results",
        metadata,
        Column("id", String, primary_key=True),
        Column("attempt_id", String, nullable=False, unique=True),
    )


def patch_migration_operations(
    migration: dict[str, Any], monkeypatch: pytest.MonkeyPatch, connection: Connection
) -> list[tuple[str, str]]:
    operations: list[tuple[str, str]] = []
    context = migration["context"]
    op = migration["op"]
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(op, "get_bind", lambda: connection)
    monkeypatch.setattr(
        op,
        "add_column",
        lambda table_name, column: operations.append(("column", column.name)),
    )
    monkeypatch.setattr(
        op,
        "create_check_constraint",
        lambda name, table_name, condition: operations.append(("constraint", name)),
    )
    return operations


def test_empty_assessment_results_allows_semantics_migration(monkeypatch):
    migration = load_migration()
    metadata = MetaData()
    foundation_result_table(metadata)
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        operations = patch_migration_operations(migration, monkeypatch, connection)
        upgrade = cast(Callable[[], None], migration["upgrade"])

        upgrade()

    assert operations == [
        ("column", "score"),
        ("column", "max_score"),
        ("column", "feedback"),
        ("constraint", "ck_assessment_results_max_score_positive"),
        ("constraint", "ck_assessment_results_score_range"),
    ]


def test_non_empty_assessment_results_fails_without_synthetic_data(monkeypatch):
    migration = load_migration()
    metadata = MetaData()
    results = foundation_result_table(metadata)
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"autocommit": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    legacy_result = {"id": "result-1", "attempt_id": "attempt-1"}

    with engine.begin() as connection:
        connection.execute(insert(results), legacy_result)
        operations = patch_migration_operations(migration, monkeypatch, connection)
        upgrade = cast(Callable[[], None], migration["upgrade"])

        with pytest.raises(RuntimeError, match="requires assessment_results to be empty"):
            upgrade()

        assert operations == []
        assert dict(connection.execute(select(results)).mappings().one()) == legacy_result
