"""Architecture guards for Learning enrollment boundaries."""

import ast
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.core.database import Base
from app.learning.application.enrollment_read import StudentEnrollmentReader
from app.learning.application.progress import ActivityProgressReader, ActivityProgressWriter
from app.learning.infrastructure import models as learning_models  # noqa: F401


def _imports(package: Path) -> set[str]:
    imports: set[str] = set()
    for source in package.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports


def test_learning_owns_enrollment_persistence_without_course_foreign_key() -> None:
    table = Base.metadata.tables["enrollments"]
    assert set(table.c.keys()) == {"id", "student_user_id", "course_id", "status", "created_at"}
    assert {key.target_fullname for key in table.foreign_keys} == {"identities.id"}
    assert not table.c.course_id.foreign_keys
    assert any(
        isinstance(constraint, UniqueConstraint)
        and set(constraint.columns.keys()) == {"student_user_id", "course_id"}
        for constraint in table.constraints
    )


def test_learning_uses_only_education_publication_application_contract() -> None:
    learning = Path(__file__).parents[1] / "app" / "learning"
    imports = _imports(learning)
    education_imports = {name for name in imports if name.startswith("app.education")}
    assert education_imports == {
        "app.education.application.activity_publication",
        "app.education.application.errors",
        "app.education.application.publication",
        "app.education.composition",
    }
    assert not {
        name
        for name in imports
        if name.startswith(("app.education.infrastructure", "app.content", "app.teacher_space"))
    }


def test_student_space_does_not_access_learning_persistence() -> None:
    student = Path(__file__).parents[1] / "app" / "student_space"
    imports = _imports(student)
    assert not {name for name in imports if name.startswith("app.learning.infrastructure")}
    assert not {name for name in imports if name.startswith("app.teacher_space.infrastructure")}


def test_student_enrollment_reader_is_minimal_read_only_contract() -> None:
    methods = {
        name
        for name, member in StudentEnrollmentReader.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    assert methods == {"list_for_student"}


def test_learning_owns_activity_progress_persistence() -> None:
    table = Base.metadata.tables["activity_progress"]
    assert set(table.c.keys()) == {
        "id",
        "student_user_id",
        "activity_id",
        "status",
        "created_at",
        "updated_at",
    }
    assert {key.target_fullname for key in table.foreign_keys} == {"identities.id"}
    assert not table.c.activity_id.foreign_keys
    assert any(
        isinstance(constraint, UniqueConstraint)
        and set(constraint.columns.keys()) == {"student_user_id", "activity_id"}
        for constraint in table.constraints
    )


def test_activity_progress_contracts_are_minimal() -> None:
    reader_methods = {
        name
        for name, member in ActivityProgressReader.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    writer_methods = {
        name
        for name, member in ActivityProgressWriter.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    assert reader_methods == {"get_for_student_activity"}
    assert writer_methods == {"start", "complete"}


def test_dashboard_readers_are_minimal_read_only_contracts() -> None:
    from app.learning.application.dashboard import ContinueLearningReader
    from app.student_space.application.dashboard import StudentDashboardReader

    continue_methods = {
        name
        for name, member in ContinueLearningReader.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    dashboard_methods = {
        name
        for name, member in StudentDashboardReader.__dict__.items()
        if callable(member) and not name.startswith("_")
    }
    assert continue_methods == {"get_for_student"}
    assert dashboard_methods == {"get_dashboard"}
