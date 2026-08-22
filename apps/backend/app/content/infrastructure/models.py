"""SQLAlchemy mapping owned by Content."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.content.domain.models import ContentStatus, ContentType
from app.core.database import Base


class ContentModel(Base):
    __tablename__ = "contents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("identities.id", ondelete="CASCADE")
    )
    type: Mapped[ContentType] = mapped_column(
        Enum(
            ContentType,
            name="content_type",
            values_callable=lambda values: [v.value for v in values],
        )
    )
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[ContentStatus] = mapped_column(
        Enum(
            ContentStatus,
            name="content_status",
            values_callable=lambda values: [v.value for v in values],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_contents_owner_created", "owner_user_id", "created_at"),)
