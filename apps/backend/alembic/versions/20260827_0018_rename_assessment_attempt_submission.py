"""Align AssessmentAttempt persistence with the approved submission contract."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260827_0018"
down_revision: str | None = "20260827_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "assessment_attempts",
        "submission_data",
        new_column_name="submission",
    )


def downgrade() -> None:
    op.alter_column(
        "assessment_attempts",
        "submission",
        new_column_name="submission_data",
    )
