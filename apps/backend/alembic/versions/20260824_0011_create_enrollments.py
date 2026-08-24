"""Create Learning-owned enrollments."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260824_0011"
down_revision: str | None = "20260824_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

enrollment_status = postgresql.ENUM(
    "enrolled", name="enrollment_status", create_type=False
)


def upgrade() -> None:
    postgresql.ENUM("enrolled", name="enrollment_status").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("status", enrollment_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_user_id"], ["identities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_user_id",
            "course_id",
            name="uq_enrollments_student_course",
        ),
    )
    op.create_index(
        op.f("ix_enrollments_student_user_id"),
        "enrollments",
        ["student_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enrollments_course_id"),
        "enrollments",
        ["course_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_enrollments_course_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_student_user_id"), table_name="enrollments")
    op.drop_table("enrollments")
    enrollment_status.drop(op.get_bind(), checkfirst=True)
