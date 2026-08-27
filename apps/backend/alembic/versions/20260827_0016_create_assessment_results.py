"""Create Assessment-owned results and complete the Attempt lifecycle."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0016"
down_revision: str | None = "20260827_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE assessment_attempt_status ADD VALUE IF NOT EXISTS 'reviewed'")
    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("assessment_attempts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("attempt_id", name="uq_assessment_results_attempt"),
    )


def downgrade() -> None:
    op.drop_table("assessment_results")
    op.execute(
        "ALTER TABLE assessment_attempts ALTER COLUMN status TYPE VARCHAR USING status::text"
    )
    op.execute("DROP TYPE assessment_attempt_status")
    op.execute("CREATE TYPE assessment_attempt_status AS ENUM ('draft', 'submitted')")
    op.execute(
        "ALTER TABLE assessment_attempts ALTER COLUMN status "
        "TYPE assessment_attempt_status USING status::text::assessment_attempt_status"
    )
