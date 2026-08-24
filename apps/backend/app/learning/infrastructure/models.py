"""SQLAlchemy mappings owned by Learning."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.learning.domain.models import EnrollmentStatus


class EnrollmentModel(Base):
    __tablename__ = "enrollments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    student_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(
            EnrollmentStatus,
            name="enrollment_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "student_user_id", "course_id", name="uq_enrollments_student_course"
        ),
    )
