"""SQLAlchemy Education repositories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.education.application.errors import (
    CourseNotFoundError,
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
    SectionNotFoundError,
)
from app.education.domain.models import Course, EducationalEnvironment, Section
from app.education.infrastructure.models import (
    CourseModel,
    EducationalEnvironmentModel,
    SectionModel,
)


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



def _course_to_domain(model: CourseModel) -> Course:
    return Course(
        id=model.id,
        educational_environment_id=model.educational_environment_id,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyCourseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, course: Course) -> Course:
        model = CourseModel(
            id=course.id,
            educational_environment_id=course.educational_environment_id,
            title=course.title,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise EnvironmentNotFoundError from error
        return _course_to_domain(model)

    def list_by_environment(self, environment_id: UUID) -> list[Course]:
        models = self.db.scalars(
            select(CourseModel)
            .where(CourseModel.educational_environment_id == environment_id)
            .order_by(CourseModel.created_at, CourseModel.id)
        ).all()
        return [_course_to_domain(model) for model in models]

    def get_in_environment(self, course_id: UUID, environment_id: UUID) -> Course | None:
        model = self.db.scalar(
            select(CourseModel).where(
                CourseModel.id == course_id,
                CourseModel.educational_environment_id == environment_id,
            )
        )
        return _course_to_domain(model) if model else None

    def update(self, course: Course) -> Course:
        model = self.db.get(CourseModel, course.id)
        if model is None:
            raise CourseNotFoundError
        model.title = course.title
        model.updated_at = course.updated_at
        self.db.flush()
        return _course_to_domain(model)



def _section_to_domain(model: SectionModel) -> Section:
    return Section(
        id=model.id,
        course_id=model.course_id,
        title=model.title,
        position=model.position,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemySectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, section: Section) -> Section:
        model = SectionModel(
            id=section.id,
            course_id=section.course_id,
            title=section.title,
            position=section.position,
            created_at=section.created_at,
            updated_at=section.updated_at,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            raise CourseNotFoundError from error
        return _section_to_domain(model)

    def list_by_course(self, course_id: UUID) -> list[Section]:
        models = self.db.scalars(
            select(SectionModel)
            .where(SectionModel.course_id == course_id)
            .order_by(SectionModel.position, SectionModel.id)
        ).all()
        return [_section_to_domain(model) for model in models]

    def get_in_course(self, section_id: UUID, course_id: UUID) -> Section | None:
        model = self.db.scalar(
            select(SectionModel).where(
                SectionModel.id == section_id,
                SectionModel.course_id == course_id,
            )
        )
        return _section_to_domain(model) if model else None

    def update(self, section: Section) -> Section:
        model = self.db.get(SectionModel, section.id)
        if model is None:
            raise SectionNotFoundError
        model.title = section.title
        model.position = section.position
        model.updated_at = section.updated_at
        self.db.flush()
        return _section_to_domain(model)

    def delete(self, section: Section) -> None:
        model = self.db.get(SectionModel, section.id)
        if model is None:
            raise SectionNotFoundError
        self.db.delete(model)
        self.db.flush()
