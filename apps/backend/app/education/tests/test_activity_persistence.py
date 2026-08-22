from typing import cast

from sqlalchemy import Enum, Index, String, Table

from app.education.infrastructure.models import ActivityModel


def test_activity_has_only_learning_unit_foreign_key() -> None:
    table = cast(Table, ActivityModel.__table__)
    keys = list(table.foreign_keys)
    assert len(keys) == 1
    assert keys[0].target_fullname == "learning_units.id"
    assert not table.c.learning_unit_id.unique
    forbidden = {"teacher_spaces", "educational_environments", "courses", "sections"}
    assert all(key.column.table.name not in forbidden for key in keys)


def test_activity_persistence_contract() -> None:
    table = cast(Table, ActivityModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "learning_unit_id",
        "title",
        "type",
        "position",
        "created_at",
        "updated_at",
    }
    assert cast(String, table.c.title.type).length == 120
    assert set(cast(Enum, table.c.type.type).enums) == {"lecture", "video", "homework"}
    assert any(
        isinstance(index, Index)
        and [column.name for column in index.columns] == ["learning_unit_id", "position"]
        for index in table.indexes
    )
