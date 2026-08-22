"""SQLAlchemy Educational Environment repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.education.application.errors import EnvironmentAlreadyExistsError
from app.education.domain.models import EducationalEnvironment
from app.education.infrastructure.models import EducationalEnvironmentModel


def _to_domain(model: EducationalEnvironmentModel) -> EducationalEnvironment:
    return EducationalEnvironment(
        id=model.id,
        teacher_space_id=model.teacher_space_id,
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyEnvironmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, environment: EducationalEnvironment) -> EducationalEnvironment:
        model = EducationalEnvironmentModel(
            id=environment.id,
            teacher_space_id=environment.teacher_space_id,
            name=environment.name,
            created_at=environment.created_at,
            updated_at=environment.updated_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise EnvironmentAlreadyExistsError from error
        return _to_domain(model)

    def get_by_teacher_space(self, teacher_space_id: UUID) -> EducationalEnvironment | None:
        model = self.db.scalar(
            select(EducationalEnvironmentModel).where(
                EducationalEnvironmentModel.teacher_space_id == teacher_space_id
            )
        )
        return _to_domain(model) if model else None

    def update(self, environment: EducationalEnvironment) -> EducationalEnvironment:
        model = self.db.get(EducationalEnvironmentModel, environment.id)
        if model is None:
            raise RuntimeError("Educational Environment disappeared during the transaction")
        model.name = environment.name
        model.updated_at = environment.updated_at
        self.db.flush()
        return _to_domain(model)
