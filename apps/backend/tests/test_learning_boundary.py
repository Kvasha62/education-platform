"""Architecture guards for Learning enrollment boundaries."""

import ast
from pathlib import Path

from app.core.database import Base
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
    assert set(table.c.keys()) == {
        "id", "student_user_id", "course_id", "status", "created_at"
    }
    assert {key.target_fullname for key in table.foreign_keys} == {"identities.id"}
    assert not table.c.course_id.foreign_keys
    assert any(
        set(constraint.columns.keys()) == {"student_user_id", "course_id"}
        for constraint in table.constraints
    )


def test_learning_uses_only_education_publication_application_contract() -> None:
    learning = Path(__file__).parents[1] / "app" / "learning"
    imports = _imports(learning)
    education_imports = {name for name in imports if name.startswith("app.education")}
    assert education_imports == {
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
