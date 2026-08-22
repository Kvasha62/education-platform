"""Education domain models."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
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
