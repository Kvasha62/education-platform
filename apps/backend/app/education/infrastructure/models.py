"""SQLAlchemy mapping owned by Education."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.education.domain.models import ActivityType


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


class LearningUnitModel(Base):
    __tablename__ = "learning_units"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    section_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_learning_units_section_position", "section_id", "position"),)


class ActivityModel(Base):
    __tablename__ = "activities"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    learning_unit_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("learning_units.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(120))
    type: Mapped[ActivityType] = mapped_column(
        Enum(
            ActivityType,
            name="activity_type",
            values_callable=lambda types: [item.value for item in types],
        )
    )
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_activities_unit_position", "learning_unit_id", "position"),)


class ActivityContentLinkModel(Base):
    __tablename__ = "activity_content_links"

    activity_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)

    __table_args__ = (Index("ix_activity_content_links_content_id", "content_id"),)
