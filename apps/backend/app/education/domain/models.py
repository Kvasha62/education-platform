"""Education domain models."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class InvalidEnvironmentNameError(ValueError):
    pass


def normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidEnvironmentNameError
    return normalized


@dataclass(frozen=True, slots=True)
class EducationalEnvironment:
    id: UUID
    teacher_space_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, teacher_space_id: UUID, name: str) -> "EducationalEnvironment":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            teacher_space_id=teacher_space_id,
            name=normalize_name(name),
            created_at=now,
            updated_at=now,
        )

    def rename(self, name: str) -> "EducationalEnvironment":
        return replace(self, name=normalize_name(name), updated_at=datetime.now(UTC))


class InvalidCourseTitleError(ValueError):
    pass


def normalize_title(title: str) -> str:
    normalized = title.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidCourseTitleError
    return normalized


@dataclass(frozen=True, slots=True)
class Course:
    id: UUID
    educational_environment_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, educational_environment_id: UUID, title: str) -> "Course":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            educational_environment_id=educational_environment_id,
            title=normalize_title(title),
            created_at=now,
            updated_at=now,
        )

    def rename(self, title: str) -> "Course":
        return replace(self, title=normalize_title(title), updated_at=datetime.now(UTC))


class InvalidSectionTitleError(ValueError):
    pass


class InvalidSectionPositionError(ValueError):
    pass


def normalize_section_title(title: str) -> str:
    normalized = title.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidSectionTitleError
    return normalized


def validate_section_position(position: int) -> int:
    if position < 0:
        raise InvalidSectionPositionError
    return position


@dataclass(frozen=True, slots=True)
class Section:
    id: UUID
    course_id: UUID
    title: str
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, course_id: UUID, title: str, position: int) -> "Section":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            course_id=course_id,
            title=normalize_section_title(title),
            position=validate_section_position(position),
            created_at=now,
            updated_at=now,
        )

    def update(self, *, title: str | None, position: int | None) -> "Section":
        return replace(
            self,
            title=self.title if title is None else normalize_section_title(title),
            position=(self.position if position is None else validate_section_position(position)),
            updated_at=datetime.now(UTC),
        )


class InvalidLearningUnitTitleError(ValueError):
    pass


class InvalidLearningUnitPositionError(ValueError):
    pass


def normalize_learning_unit_title(title: str) -> str:
    normalized = title.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidLearningUnitTitleError
    return normalized


def validate_learning_unit_position(position: int) -> int:
    if position < 0:
        raise InvalidLearningUnitPositionError
    return position


@dataclass(frozen=True, slots=True)
class LearningUnit:
    id: UUID
    section_id: UUID
    title: str
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, section_id: UUID, title: str, position: int) -> "LearningUnit":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            section_id=section_id,
            title=normalize_learning_unit_title(title),
            position=validate_learning_unit_position(position),
            created_at=now,
            updated_at=now,
        )

    def update(self, *, title: str | None, position: int | None) -> "LearningUnit":
        return replace(
            self,
            title=self.title if title is None else normalize_learning_unit_title(title),
            position=self.position
            if position is None
            else validate_learning_unit_position(position),
            updated_at=datetime.now(UTC),
        )


class ActivityType(StrEnum):
    LECTURE = "lecture"
    VIDEO = "video"
    HOMEWORK = "homework"


class InvalidActivityTitleError(ValueError):
    pass


class InvalidActivityPositionError(ValueError):
    pass


class InvalidActivityTypeError(ValueError):
    pass


def normalize_activity_title(title: str) -> str:
    normalized = title.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidActivityTitleError
    return normalized


def validate_activity_position(position: int) -> int:
    if position < 0:
        raise InvalidActivityPositionError
    return position


@dataclass(frozen=True, slots=True)
class Activity:
    id: UUID
    learning_unit_id: UUID
    title: str
    type: ActivityType
    position: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls, learning_unit_id: UUID, title: str, activity_type: ActivityType, position: int
    ) -> "Activity":
        if not isinstance(activity_type, ActivityType):
            raise InvalidActivityTypeError
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            learning_unit_id=learning_unit_id,
            title=normalize_activity_title(title),
            type=activity_type,
            position=validate_activity_position(position),
            created_at=now,
            updated_at=now,
        )

    def update(self, *, title: str | None, position: int | None) -> "Activity":
        return replace(
            self,
            title=self.title if title is None else normalize_activity_title(title),
            position=self.position if position is None else validate_activity_position(position),
            updated_at=datetime.now(UTC),
        )
