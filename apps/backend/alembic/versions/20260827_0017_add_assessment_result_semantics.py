"""Add approved scoring and feedback fields to AssessmentResult."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0017"
down_revision: str | None = "20260827_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADR-0007 forbids inventing score defaults for existing foundation rows.
    op.add_column(
        "assessment_results",
        sa.Column("score", sa.Integer(), nullable=False),
    )
    op.add_column(
        "assessment_results",
        sa.Column("max_score", sa.Integer(), nullable=False),
    )
    op.add_column(
        "assessment_results",
        sa.Column("feedback", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_assessment_results_max_score_positive",
        "assessment_results",
        "max_score > 0",
    )
    op.create_check_constraint(
        "ck_assessment_results_score_range",
        "assessment_results",
        "score >= 0 AND score <= max_score",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_assessment_results_score_range",
        "assessment_results",
        type_="check",
    )
    op.drop_constraint(
        "ck_assessment_results_max_score_positive",
        "assessment_results",
        type_="check",
    )
    op.drop_column("assessment_results", "feedback")
    op.drop_column("assessment_results", "max_score")
    op.drop_column("assessment_results", "score")
