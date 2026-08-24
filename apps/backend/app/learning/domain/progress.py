"""Learning-owned Activity progress model."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class ActivityProgress:
    id: UUID
    student_user_id: UUID
    activity_id: UUID
    status: ProgressStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def start(cls, student_user_id: UUID, activity_id: UUID) -> "ActivityProgress":
        now = datetime.now(UTC)
        return cls(uuid4(), student_user_id, activity_id, ProgressStatus.IN_PROGRESS, now, now)

    def complete(self) -> "ActivityProgress":
        if self.status is ProgressStatus.COMPLETED:
            return self
        return replace(self, status=ProgressStatus.COMPLETED, updated_at=datetime.now(UTC))
