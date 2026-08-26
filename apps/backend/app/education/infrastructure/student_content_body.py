"""Education-owned published Activity/Content association lookup."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.education.domain.models import CourseStatus
from app.education.infrastructure.models import (
    ActivityContentLinkModel,
    ActivityModel,
    CourseModel,
    LearningUnitModel,
    SectionModel,
)


class SqlAlchemyPublishedContentAssociationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_linked_to_published_course(self, content_id: UUID) -> bool:
        return self.db.scalar(
            select(ActivityContentLinkModel.content_id)
            .join(ActivityModel, ActivityContentLinkModel.activity_id == ActivityModel.id)
            .join(LearningUnitModel, ActivityModel.learning_unit_id == LearningUnitModel.id)
            .join(SectionModel, LearningUnitModel.section_id == SectionModel.id)
            .join(CourseModel, SectionModel.course_id == CourseModel.id)
            .where(
                ActivityContentLinkModel.content_id == content_id,
                CourseModel.status == CourseStatus.PUBLISHED,
            )
            .limit(1)
        ) is not None
