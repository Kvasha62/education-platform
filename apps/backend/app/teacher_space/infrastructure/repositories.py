"""SQLAlchemy Teacher Space repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.teacher_space.domain.models import TeacherSpace
from app.teacher_space.infrastructure.models import TeacherSpaceModel


def _to_domain(model: TeacherSpaceModel) -> TeacherSpace:
    return TeacherSpace(
        id=model.id,
        owner_user_id=model.owner_user_id,
        name=model.name,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyTeacherSpaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, teacher_space: TeacherSpace) -> TeacherSpace:
        model = TeacherSpaceModel(
            id=teacher_space.id,
            owner_user_id=teacher_space.owner_user_id,
            name=teacher_space.name,
            status=teacher_space.status,
            created_at=teacher_space.created_at,
            updated_at=teacher_space.updated_at,
        )
        self.db.add(model)
        self.db.flush()
        return _to_domain(model)

    def list_owned(self, owner_user_id: UUID) -> list[TeacherSpace]:
        models = self.db.scalars(
            select(TeacherSpaceModel)
            .where(TeacherSpaceModel.owner_user_id == owner_user_id)
            .order_by(TeacherSpaceModel.created_at, TeacherSpaceModel.id)
        ).all()
        return [_to_domain(model) for model in models]

    def get_by_id(self, teacher_space_id: UUID) -> TeacherSpace | None:
        model = self.db.scalar(
            select(TeacherSpaceModel).where(TeacherSpaceModel.id == teacher_space_id)
        )
        return _to_domain(model) if model else None

    def get_owned(self, teacher_space_id: UUID, owner_user_id: UUID) -> TeacherSpace | None:
        model = self.db.scalar(
            select(TeacherSpaceModel).where(
                TeacherSpaceModel.id == teacher_space_id,
                TeacherSpaceModel.owner_user_id == owner_user_id,
            )
        )
        return _to_domain(model) if model else None

    def update(self, teacher_space: TeacherSpace) -> TeacherSpace:
        model = self.db.get(TeacherSpaceModel, teacher_space.id)
        if model is None:  # The application already resolved the owned aggregate.
            raise RuntimeError("Teacher Space disappeared during the transaction")
        model.name = teacher_space.name
        model.status = teacher_space.status
        model.updated_at = teacher_space.updated_at
        self.db.flush()
        return _to_domain(model)
