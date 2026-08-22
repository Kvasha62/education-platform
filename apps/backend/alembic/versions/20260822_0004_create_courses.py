"""Create Course schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_0004"
down_revision: str | None = "20260822_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("educational_environment_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["educational_environment_id"],
            ["educational_environments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_courses_educational_environment_id",
        "courses",
        ["educational_environment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_courses_educational_environment_id", table_name="courses")
    op.drop_table("courses")
