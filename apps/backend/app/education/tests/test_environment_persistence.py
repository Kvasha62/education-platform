from typing import cast

from sqlalchemy import Table, UniqueConstraint

from app.education.infrastructure.models import EducationalEnvironmentModel


def test_teacher_space_reference_is_unique_without_database_foreign_key() -> None:
    table = cast(Table, EducationalEnvironmentModel.__table__)

    assert not table.foreign_keys
    assert any(
        isinstance(constraint, UniqueConstraint)
        and [column.name for column in constraint.columns] == ["teacher_space_id"]
        for constraint in table.constraints
    )
