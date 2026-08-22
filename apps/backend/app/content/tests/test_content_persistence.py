from typing import cast

from sqlalchemy import Enum, Index, String, Table

from app.content.infrastructure.models import ContentModel


def test_content_persistence_contract_and_owner_fk() -> None:
    table = cast(Table, ContentModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "owner_user_id",
        "type",
        "title",
        "status",
        "created_at",
        "updated_at",
    }
    assert {key.target_fullname for key in table.foreign_keys} == {"identities.id"}
    assert cast(String, table.c.title.type).length == 120
    assert set(cast(Enum, table.c.type.type).enums) == {"article", "resource"}
    assert set(cast(Enum, table.c.status.type).enums) == {"draft", "published"}
    assert any(
        isinstance(index, Index)
        and [column.name for column in index.columns] == ["owner_user_id", "created_at"]
        for index in table.indexes
    )


def test_content_has_no_education_or_teacher_foreign_keys() -> None:
    forbidden = {
        "teacher_spaces",
        "educational_environments",
        "courses",
        "sections",
        "learning_units",
        "activities",
    }
    table = cast(Table, ContentModel.__table__)
    assert all(key.column.table.name not in forbidden for key in table.foreign_keys)
