from typing import cast

from sqlalchemy import Index, String, Table

from app.education.infrastructure.models import LearningUnitModel


def test_learning_unit_references_only_section_table() -> None:
    table = cast(Table, LearningUnitModel.__table__)
    foreign_keys = list(table.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "sections.id"
    assert all("teacher_spaces" not in key.target_fullname for key in foreign_keys)
    assert not table.c.section_id.unique


def test_learning_unit_persistence_contract() -> None:
    table = cast(Table, LearningUnitModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "section_id",
        "title",
        "position",
        "created_at",
        "updated_at",
    }
    assert cast(String, table.c.title.type).length == 120
    assert any(
        isinstance(index, Index)
        and [column.name for column in index.columns] == ["section_id", "position"]
        for index in table.indexes
    )
