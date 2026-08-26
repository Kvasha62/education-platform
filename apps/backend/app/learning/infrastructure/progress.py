from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.learning.domain.models import EnrollmentStatus
from app.learning.domain.progress import ActivityProgress, ProgressStatus
from app.learning.infrastructure.models import ActivityProgressModel, EnrollmentModel


def _to_domain(model: ActivityProgressModel) -> ActivityProgress:
    return ActivityProgress(
        model.id,
        model.student_user_id,
        model.activity_id,
        model.status,
        model.created_at,
        model.updated_at,
    )


class SqlAlchemyProgressRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgress | None:
        model = self.db.scalar(
            select(ActivityProgressModel).where(
                ActivityProgressModel.student_user_id == student_user_id,
                ActivityProgressModel.activity_id == activity_id,
            )
        )
        return _to_domain(model) if model else None

    def list_in_progress(self, student_user_id: UUID) -> list[ActivityProgress]:
        models = self.db.scalars(
            select(ActivityProgressModel)
            .where(
                ActivityProgressModel.student_user_id == student_user_id,
                ActivityProgressModel.status == ProgressStatus.IN_PROGRESS,
            )
            .order_by(ActivityProgressModel.updated_at.desc(), ActivityProgressModel.id.desc())
        ).all()
        return [_to_domain(model) for model in models]

    def get_or_create(self, progress: ActivityProgress) -> ActivityProgress:
        model = ActivityProgressModel(
            id=progress.id,
            student_user_id=progress.student_user_id,
            activity_id=progress.activity_id,
            status=progress.status,
            created_at=progress.created_at,
            updated_at=progress.updated_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError:
            existing = self.get(progress.student_user_id, progress.activity_id)
            if existing is None:
                raise
            return existing
        return _to_domain(model)

    def update(self, progress: ActivityProgress) -> ActivityProgress:
        model = self.db.get(ActivityProgressModel, progress.id)
        if model is None:
            raise RuntimeError("Activity progress disappeared")
        model.status, model.updated_at = progress.status, progress.updated_at
        self.db.flush()
        return _to_domain(model)


class SqlAlchemyEnrollmentVerifier:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_status(self, student_user_id: UUID, course_id: UUID) -> EnrollmentStatus | None:
        return self.db.scalar(
            select(EnrollmentModel.status).where(
                EnrollmentModel.student_user_id == student_user_id,
                EnrollmentModel.course_id == course_id,
            )
        )
