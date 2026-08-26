"""Learning-owned Continue Learning dashboard reader."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from app.education.application.activity_publication import PublishedActivityCollectionLookup
from app.learning.domain.progress import ActivityProgress


@dataclass(frozen=True, slots=True)
class ContinueLearningReference:
    course_id: UUID
    activity_id: UUID
    activity_title: str
    status: Literal["in_progress"]
    updated_at: datetime


class InProgressRepository(Protocol):
    def list_in_progress(self, student_user_id: UUID) -> list[ActivityProgress]: ...


class ContinueLearningReader(Protocol):
    def get_for_student(
        self, student_user_id: UUID, enrolled_course_ids: set[UUID]
    ) -> ContinueLearningReference | None: ...


class ContinueLearningService:
    """Select the most recently updated visible IN_PROGRESS Activity."""

    def __init__(
        self,
        progress: InProgressRepository,
        activities: PublishedActivityCollectionLookup,
    ) -> None:
        self.progress = progress
        self.activities = activities

    def get_for_student(
        self, student_user_id: UUID, enrolled_course_ids: set[UUID]
    ) -> ContinueLearningReference | None:
        if not enrolled_course_ids:
            return None
        candidates = self.progress.list_in_progress(student_user_id)
        published = self.activities.list_published(
            [candidate.activity_id for candidate in candidates],
            enrolled_course_ids,
        )
        for candidate in candidates:
            activity = published.get(candidate.activity_id)
            if activity is not None:
                return ContinueLearningReference(
                    course_id=activity.course_id,
                    activity_id=candidate.activity_id,
                    activity_title=activity.title,
                    status="in_progress",
                    updated_at=candidate.updated_at,
                )
        return None
