from typing import cast

from sqlalchemy import Index, String, Table

from app.education.infrastructure.models import SectionModel


def test_section_references_only_course_table() -> None:
    table = cast(Table, SectionModel.__table__)
    foreign_keys = list(table.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "courses.id"
    assert all("teacher_spaces" not in foreign_key.target_fullname for foreign_key in foreign_keys)
    assert not table.c.course_id.unique


def test_section_persistence_contract_and_listing_index() -> None:
    table = cast(Table, SectionModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "course_id",
        "title",
        "position",
        "created_at",
        "updated_at",
    }
    assert cast(String, table.c.title.type).length == 120
    assert any(
        isinstance(index, Index)
        and [column.name for column in index.columns] == ["course_id", "position"]
        for index in table.indexes
    )
