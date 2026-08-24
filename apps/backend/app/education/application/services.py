"""Education use cases."""

from uuid import UUID

from app.education.application.errors import (
    ActivityNotFoundError,
    CourseNotFoundError,
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
    LearningUnitNotFoundError,
    SectionNotFoundError,
)
from app.education.application.ports import (
    ActivityRepository,
    CourseRepository,
    EnvironmentRepository,
    LearningUnitRepository,
    SectionRepository,
)
from app.education.domain.models import (
    Activity,
    ActivityType,
    Course,
    EducationalEnvironment,
    LearningUnit,
    Section,
)


class EducationalEnvironmentService:
    def __init__(self, repository: EnvironmentRepository) -> None:
        self.repository = repository

    def create(self, teacher_space_id: UUID, name: str) -> EducationalEnvironment:
        if self.repository.get_by_teacher_space(teacher_space_id) is not None:
            raise EnvironmentAlreadyExistsError
        return self.repository.add(EducationalEnvironment.create(teacher_space_id, name))

    def get(self, teacher_space_id: UUID) -> EducationalEnvironment:
        environment = self.repository.get_by_teacher_space(teacher_space_id)
        if environment is None:
            raise EnvironmentNotFoundError
        return environment

    def rename(self, teacher_space_id: UUID, name: str) -> EducationalEnvironment:
        return self.repository.update(self.get(teacher_space_id).rename(name))


class CourseService:
    def __init__(self, repository: CourseRepository) -> None:
        self.repository = repository

    def create(self, environment_id: UUID, title: str) -> Course:
        return self.repository.add(Course.create(environment_id, title))

    def list(self, environment_id: UUID) -> list[Course]:
        return self.repository.list_by_environment(environment_id)

    def get(self, course_id: UUID, environment_id: UUID) -> Course:
        course = self.repository.get_in_environment(course_id, environment_id)
        if course is None:
            raise CourseNotFoundError
        return course

    def rename(self, course_id: UUID, environment_id: UUID, title: str) -> Course:
        return self.repository.update(self.get(course_id, environment_id).rename(title))

    def publish(self, course_id: UUID, environment_id: UUID) -> Course:
        course = self.get(course_id, environment_id)
        published = course.publish()
        return course if published is course else self.repository.update(published)

    def archive(self, course_id: UUID, environment_id: UUID) -> Course:
        course = self.get(course_id, environment_id)
        archived = course.archive()
        return course if archived is course else self.repository.update(archived)


class SectionService:
    def __init__(self, repository: SectionRepository) -> None:
        self.repository = repository

    def create(self, course_id: UUID, title: str, position: int) -> Section:
        return self.repository.add(Section.create(course_id, title, position))

    def list(self, course_id: UUID) -> list[Section]:
        return self.repository.list_by_course(course_id)

    def get(self, section_id: UUID, course_id: UUID) -> Section:
        section = self.repository.get_in_course(section_id, course_id)
        if section is None:
            raise SectionNotFoundError
        return section

    def update(
        self,
        section_id: UUID,
        course_id: UUID,
        *,
        title: str | None,
        position: int | None,
    ) -> Section:
        section = self.get(section_id, course_id)
        return self.repository.update(section.update(title=title, position=position))

    def delete(self, section_id: UUID, course_id: UUID) -> None:
        self.repository.delete(self.get(section_id, course_id))


class LearningUnitService:
    def __init__(self, repository: LearningUnitRepository) -> None:
        self.repository = repository

    def create(self, section_id: UUID, title: str, position: int) -> LearningUnit:
        return self.repository.add(LearningUnit.create(section_id, title, position))

    def list(self, section_id: UUID) -> list[LearningUnit]:
        return self.repository.list_by_section(section_id)

    def get(self, unit_id: UUID, section_id: UUID) -> LearningUnit:
        unit = self.repository.get_in_section(unit_id, section_id)
        if unit is None:
            raise LearningUnitNotFoundError
        return unit

    def update(
        self, unit_id: UUID, section_id: UUID, *, title: str | None, position: int | None
    ) -> LearningUnit:
        unit = self.get(unit_id, section_id)
        return self.repository.update(unit.update(title=title, position=position))

    def delete(self, unit_id: UUID, section_id: UUID) -> None:
        self.repository.delete(self.get(unit_id, section_id))


class ActivityService:
    def __init__(self, repository: ActivityRepository) -> None:
        self.repository = repository

    def create(
        self, unit_id: UUID, title: str, activity_type: ActivityType, position: int
    ) -> Activity:
        return self.repository.add(Activity.create(unit_id, title, activity_type, position))

    def list(self, unit_id: UUID) -> list[Activity]:
        return self.repository.list_by_unit(unit_id)

    def get(self, activity_id: UUID, unit_id: UUID) -> Activity:
        activity = self.repository.get_in_unit(activity_id, unit_id)
        if activity is None:
            raise ActivityNotFoundError
        return activity

    def update(
        self, activity_id: UUID, unit_id: UUID, *, title: str | None, position: int | None
    ) -> Activity:
        activity = self.get(activity_id, unit_id)
        return self.repository.update(activity.update(title=title, position=position))

    def delete(self, activity_id: UUID, unit_id: UUID) -> None:
        self.repository.delete(self.get(activity_id, unit_id))
