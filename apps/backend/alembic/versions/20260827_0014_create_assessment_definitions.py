"""Create Assessment-owned AssessmentDefinition foundation."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0014"
down_revision: str | None = "20260825_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = sa.Enum("active", "archived", name="assessment_definition_status")
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "assessment_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", status, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", name="uq_assessment_definitions_activity"),
    )


def downgrade() -> None:
    op.drop_table("assessment_definitions")
    sa.Enum(name="assessment_definition_status").drop(op.get_bind(), checkfirst=True)
