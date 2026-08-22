from typing import cast

from sqlalchemy import String, Table

from app.education.infrastructure.models import CourseModel


def test_course_references_only_education_environment_table() -> None:
    table = cast(Table, CourseModel.__table__)
    foreign_keys = list(table.foreign_keys)

    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "educational_environments.id"
    assert all("teacher_spaces" not in foreign_key.target_fullname for foreign_key in foreign_keys)
    assert not table.c.educational_environment_id.unique


def test_course_persistence_has_required_fields() -> None:
    table = cast(Table, CourseModel.__table__)
    assert set(table.c.keys()) == {
        "id",
        "educational_environment_id",
        "title",
        "created_at",
        "updated_at",
    }
    assert cast(String, table.c.title.type).length == 120
