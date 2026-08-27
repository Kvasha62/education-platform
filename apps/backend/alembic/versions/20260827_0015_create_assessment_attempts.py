"""Create Assessment-owned attempts."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0015"
down_revision: str | None = "20260827_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    status = sa.Enum("draft", "submitted", name="assessment_attempt_status")
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "assessment_definition_id",
            sa.Uuid(),
            sa.ForeignKey("assessment_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("submission_data", sa.Text(), nullable=True),
        sa.Column("status", status, nullable=False),
    )
    op.create_index(
        "ix_assessment_attempts_assessment_definition_id",
        "assessment_attempts",
        ["assessment_definition_id"],
    )
    op.create_index("ix_assessment_attempts_student_id", "assessment_attempts", ["student_id"])


def downgrade():
    op.drop_index("ix_assessment_attempts_student_id", table_name="assessment_attempts")
    op.drop_index(
        "ix_assessment_attempts_assessment_definition_id", table_name="assessment_attempts"
    )
    op.drop_table("assessment_attempts")
    sa.Enum(name="assessment_attempt_status").drop(op.get_bind(), checkfirst=True)
