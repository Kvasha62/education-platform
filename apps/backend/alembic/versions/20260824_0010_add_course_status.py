"""Add Course lifecycle status."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260824_0010"
down_revision: str | None = "20260822_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

course_status = postgresql.ENUM(
    "draft",
    "published",
    "archived",
    name="course_status",
    create_type=False,
)


def upgrade() -> None:
    postgresql.ENUM(
        "draft",
        "published",
        "archived",
        name="course_status",
    ).create(op.get_bind(), checkfirst=True)
    op.add_column(
        "courses",
        sa.Column(
            "status",
            course_status,
            nullable=False,
            server_default="draft",
        ),
    )
    op.alter_column("courses", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("courses", "status")
    course_status.drop(op.get_bind(), checkfirst=True)
