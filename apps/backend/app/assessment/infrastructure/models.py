from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.models import AssessmentDefinitionStatus
from app.core.database import Base


class AssessmentDefinitionModel(Base):
    __tablename__ = "assessment_definitions"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    activity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AssessmentDefinitionStatus] = mapped_column(
        Enum(
            AssessmentDefinitionStatus,
            name="assessment_definition_status",
            values_callable=lambda values: [value.value for value in values],
        )
    )
    __table_args__ = (UniqueConstraint("activity_id", name="uq_assessment_definitions_activity"),)


from app.assessment.domain.attempts import AssessmentAttemptStatus


class AssessmentAttemptModel(Base):
    __tablename__ = "assessment_attempts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    assessment_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    submission_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AssessmentAttemptStatus] = mapped_column(
        Enum(
            AssessmentAttemptStatus,
            name="assessment_attempt_status",
            values_callable=lambda values: [value.value for value in values],
        )
    )
