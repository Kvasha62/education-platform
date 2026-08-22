from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import String, Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.education.application.errors import CourseNotFoundError, EnvironmentNotFoundError
from app.education.domain.models import Course
from app.education.infrastructure.models import CourseModel
from app.education.infrastructure.repositories import SqlAlchemyCourseRepository


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


def test_add_translates_integrity_error_to_environment_not_found() -> None:
    session = MagicMock(spec=Session)
    session.flush.side_effect = IntegrityError("INSERT", {}, Exception("constraint"))
    repository = SqlAlchemyCourseRepository(cast(Session, session))

    with pytest.raises(EnvironmentNotFoundError):
        repository.add(Course.create(uuid4(), "Course"))


def test_update_missing_course_raises_course_not_found() -> None:
    session = MagicMock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyCourseRepository(cast(Session, session))

    with pytest.raises(CourseNotFoundError):
        repository.update(Course.create(uuid4(), "Course"))
