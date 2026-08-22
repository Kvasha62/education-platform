"""SQLAlchemy mapping owned by Education."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EducationalEnvironmentModel(Base):
    __tablename__ = "educational_environments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    teacher_space_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CourseModel(Base):
    __tablename__ = "courses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    educational_environment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("educational_environments.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SectionModel(Base):
    __tablename__ = "sections"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.id", ondelete="CASCADE"),
    )
    title: Mapped[str] = mapped_column(String(120))
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_sections_course_position", "course_id", "position"),)
