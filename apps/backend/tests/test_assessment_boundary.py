import ast
from pathlib import Path

from app.assessment.infrastructure import models as assessment_models  # noqa: F401
from app.core.database import Base


def _imports(package: Path) -> set[str]:
    imports: set[str] = set()
    for source in package.rglob("*.py"):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports


def test_assessment_definition_persistence_is_assessment_owned() -> None:
    table = Base.metadata.tables["assessment_definitions"]
    assert set(table.c.keys()) == {"id", "activity_id", "instructions", "status"}
    assert not table.foreign_keys
    assert any(
        constraint.name == "uq_assessment_definitions_activity"
        for constraint in table.constraints
    )


def test_assessment_result_persistence_is_assessment_owned() -> None:
    table = Base.metadata.tables["assessment_results"]
    assert set(table.c.keys()) == {
        "id",
        "attempt_id",
        "score",
        "max_score",
        "feedback",
    }
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "assessment_attempts.id"
    }
    assert any(
        constraint.name == "uq_assessment_results_attempt"
        for constraint in table.constraints
    )


def test_assessment_does_not_access_other_context_persistence_or_learning() -> None:
    assessment = Path(__file__).parents[1] / "app" / "assessment"
    imports = _imports(assessment)
    assert not {
        name
        for name in imports
        if name.startswith(
            (
                "app.education.infrastructure",
                "app.teacher_space.infrastructure",
                "app.learning",
                "app.student_space.infrastructure",
            )
        )
    }


def test_education_scope_boundary_does_not_import_teacher_space() -> None:
    education_scope = Path(__file__).parents[1] / "app" / "education" / "application" / "activity_scope.py"
    assert not {
        name
        for name in _imports(education_scope.parent)
        if name.startswith("app.teacher_space")
    }
