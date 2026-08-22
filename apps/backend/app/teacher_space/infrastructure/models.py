"""SQLAlchemy mapping owned by Teacher Space."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.teacher_space.domain.models import TeacherSpaceStatus


class TeacherSpaceModel(Base):
    __tablename__ = "teacher_spaces"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[TeacherSpaceStatus] = mapped_column(
        Enum(
            TeacherSpaceStatus,
            name="teacher_space_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
