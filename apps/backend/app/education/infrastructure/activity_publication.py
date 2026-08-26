"""Education-owned published Activity lookup persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.education.application.activity_publication import PublishedActivityReference
from app.education.domain.models import CourseStatus
from app.education.infrastructure.models import (
    ActivityModel,
    CourseModel,
    LearningUnitModel,
    SectionModel,
)


class SqlAlchemyPublishedActivityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lookup_published(self, activity_id: UUID) -> PublishedActivityReference | None:
        row = self.db.execute(
            select(ActivityModel.id, CourseModel.id)
            .join(LearningUnitModel, ActivityModel.learning_unit_id == LearningUnitModel.id)
            .join(SectionModel, LearningUnitModel.section_id == SectionModel.id)
            .join(CourseModel, SectionModel.course_id == CourseModel.id)
            .where(ActivityModel.id == activity_id, CourseModel.status == CourseStatus.PUBLISHED)
        ).one_or_none()
        return PublishedActivityReference(row[0], row[1]) if row else None

    def list_published(
        self, activity_ids: list[UUID]
    ) -> list[PublishedActivityReference]:
        if not activity_ids:
            return []
        rows = self.db.execute(
            select(ActivityModel.id, CourseModel.id)
            .join(LearningUnitModel, ActivityModel.learning_unit_id == LearningUnitModel.id)
            .join(SectionModel, LearningUnitModel.section_id == SectionModel.id)
            .join(CourseModel, SectionModel.course_id == CourseModel.id)
            .where(
                ActivityModel.id.in_(activity_ids),
                CourseModel.status == CourseStatus.PUBLISHED,
            )
        ).all()
        return [PublishedActivityReference(row[0], row[1]) for row in rows]
