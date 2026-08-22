"""Create Content schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_0008"
down_revision: str | None = "20260822_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
content_type = sa.Enum("article", "resource", name="content_type")
content_status = sa.Enum("draft", "published", name="content_status")


def upgrade() -> None:
    op.create_table(
        "contents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("type", content_type, nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("status", content_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["identities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contents_owner_created", "contents", ["owner_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_contents_owner_created", table_name="contents")
    op.drop_table("contents")
    content_status.drop(op.get_bind(), checkfirst=True)
    content_type.drop(op.get_bind(), checkfirst=True)
