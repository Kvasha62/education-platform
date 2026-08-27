from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment.domain.attempts import AssessmentAttemptStatus
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
    submission: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AssessmentAttemptStatus] = mapped_column(
        Enum(
            AssessmentAttemptStatus,
            name="assessment_attempt_status",
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
    )


class AssessmentResultModel(Base):
    __tablename__ = "assessment_results"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    attempt_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_attempts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_assessment_results_attempt"),
        CheckConstraint("max_score > 0", name="ck_assessment_results_max_score_positive"),
        CheckConstraint(
            "score >= 0 AND score <= max_score",
            name="ck_assessment_results_score_range",
        ),
    )
