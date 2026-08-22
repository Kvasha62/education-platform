"""Teacher Space domain model without framework or persistence dependencies."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class TeacherSpaceStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class InvalidTeacherSpaceNameError(ValueError):
    pass


class TeacherSpaceDisabledError(Exception):
    pass


class InvalidTeacherSpaceTransitionError(Exception):
    pass


def normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidTeacherSpaceNameError
    return normalized


@dataclass(frozen=True, slots=True)
class TeacherSpace:
    id: UUID
    owner_user_id: UUID
    name: str
    status: TeacherSpaceStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, owner_user_id: UUID, name: str) -> "TeacherSpace":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            owner_user_id=owner_user_id,
            name=normalize_name(name),
            status=TeacherSpaceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def rename(self, name: str) -> "TeacherSpace":
        if self.status is TeacherSpaceStatus.DISABLED:
            raise TeacherSpaceDisabledError
        return replace(self, name=normalize_name(name), updated_at=datetime.now(UTC))

    def disable(self) -> "TeacherSpace":
        if self.status is not TeacherSpaceStatus.ACTIVE:
            raise InvalidTeacherSpaceTransitionError
        return replace(self, status=TeacherSpaceStatus.DISABLED, updated_at=datetime.now(UTC))
