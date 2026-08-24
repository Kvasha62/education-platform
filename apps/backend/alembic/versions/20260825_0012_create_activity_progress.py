"""Create Learning-owned Activity progress."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260825_0012"
down_revision: str | None = "20260824_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
progress_status = postgresql.ENUM(
    "not_started", "in_progress", "completed", name="progress_status", create_type=False
)


def upgrade() -> None:
    postgresql.ENUM("not_started", "in_progress", "completed", name="progress_status").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "activity_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("status", progress_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_user_id"], ["identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_user_id", "activity_id", name="uq_activity_progress_student_activity"
        ),
    )
    op.create_index(
        op.f("ix_activity_progress_student_user_id"),
        "activity_progress",
        ["student_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_activity_progress_activity_id"), "activity_progress", ["activity_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_progress_activity_id"), table_name="activity_progress")
    op.drop_index(op.f("ix_activity_progress_student_user_id"), table_name="activity_progress")
    op.drop_table("activity_progress")
    progress_status.drop(op.get_bind(), checkfirst=True)
