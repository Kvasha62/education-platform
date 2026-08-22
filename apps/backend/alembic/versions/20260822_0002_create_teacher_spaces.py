"""Create Teacher Space ownership schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_0002"
down_revision: str | None = "20260821_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

teacher_space_status = sa.Enum("active", "disabled", name="teacher_space_status")


def upgrade() -> None:
    op.create_table(
        "teacher_spaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", teacher_space_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_spaces_owner_user_id", "teacher_spaces", ["owner_user_id"])


def downgrade() -> None:
    op.drop_index("ix_teacher_spaces_owner_user_id", table_name="teacher_spaces")
    op.drop_table("teacher_spaces")
    teacher_space_status.drop(op.get_bind(), checkfirst=True)
