"""Add Content-owned structured body persistence."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260825_0013"
down_revision: str | None = "20260825_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contents", sa.Column("body", postgresql.JSONB(), nullable=True))
    op.execute(
        sa.text(
            r"""
            UPDATE contents
            SET body = CASE
                WHEN type = 'article' THEN
                    '{"schema_version"\:1,"kind"\:"article","blocks"\:[]}'::jsonb
                ELSE
                    '{"schema_version"\:1,"kind"\:"resource","resource"\:{"url"\:null,"description"\:""}}'::jsonb
            END
            """
        )
    )
    op.alter_column("contents", "body", existing_type=postgresql.JSONB(), nullable=False)


def downgrade() -> None:
    op.drop_column("contents", "body")
