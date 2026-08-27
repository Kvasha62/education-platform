"""Add approved scoring and feedback fields to AssessmentResult."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260827_0017"
down_revision: str | None = "20260827_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPTY_TABLE_ERROR = (
    "EDU-061 migration requires assessment_results to be empty; "
    "existing EDU-059 Results need a separately approved migration policy"
)


def _require_empty_assessment_results() -> None:
    if context.is_offline_mode():
        op.execute(
            sa.text(
                f"""
DO $edu061$
BEGIN
    IF EXISTS (SELECT 1 FROM assessment_results) THEN
        RAISE EXCEPTION '{EMPTY_TABLE_ERROR}';
    END IF;
END
$edu061$
"""
            )
        )
        return

    existing_result = op.get_bind().execute(
        sa.text("SELECT 1 FROM assessment_results LIMIT 1")
    ).first()
    if existing_result is not None:
        raise RuntimeError(EMPTY_TABLE_ERROR)


def upgrade() -> None:
    _require_empty_assessment_results()
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
