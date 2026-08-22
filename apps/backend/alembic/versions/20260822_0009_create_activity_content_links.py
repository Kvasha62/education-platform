"""Create Education-owned Activity / Content association."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_0009"
down_revision: str | None = "20260822_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "activity_content_links",
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("activity_id", "content_id"),
    )
    op.create_index(
        "ix_activity_content_links_content_id",
        "activity_content_links",
        ["content_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_activity_content_links_content_id",
        table_name="activity_content_links",
    )
    op.drop_table("activity_content_links")
