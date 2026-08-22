"""SQLAlchemy mapping owned by Education."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EducationalEnvironmentModel(Base):
    __tablename__ = "educational_environments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    teacher_space_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("teacher_spaces.id", ondelete="CASCADE"),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
