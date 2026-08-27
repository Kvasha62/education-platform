from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.education.infrastructure.models import (
    ActivityModel,
    CourseModel,
    EducationalEnvironmentModel,
    LearningUnitModel,
    SectionModel,
)


class SqlAlchemyActivityTeacherSpaceScopeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def belongs_to_teacher_space(self, activity_id: UUID, teacher_space_id: UUID) -> bool:
        return (
            self.db.scalar(
                select(ActivityModel.id)
                .join(LearningUnitModel)
                .join(SectionModel)
                .join(CourseModel)
                .join(EducationalEnvironmentModel)
                .where(
                    ActivityModel.id == activity_id,
                    EducationalEnvironmentModel.teacher_space_id == teacher_space_id,
                )
            )
            is not None
        )
