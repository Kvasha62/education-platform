"""Activity progress application contracts and use cases."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.application.activity_publication import PublishedActivityLookup
from app.education.application.errors import PublishedActivityNotFoundError
from app.learning.domain.models import EnrollmentStatus
from app.learning.domain.progress import ActivityProgress, ProgressStatus


@dataclass(frozen=True, slots=True)
class ActivityProgressReference:
    activity_id: UUID
    status: ProgressStatus


class ActivityProgressReader(Protocol):
    def get_for_student_activity(
        self, student_user_id: UUID, activity_id: UUID
    ) -> ActivityProgressReference | None: ...


class ActivityProgressWriter(Protocol):
    def start(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgressReference: ...
    def complete(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgressReference: ...


class ProgressRepository(Protocol):
    def get(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgress | None: ...
    def get_or_create(self, progress: ActivityProgress) -> ActivityProgress: ...
    def update(self, progress: ActivityProgress) -> ActivityProgress: ...


class EnrollmentVerifier(Protocol):
    def get_status(self, student_user_id: UUID, course_id: UUID) -> EnrollmentStatus | None: ...


class ProgressActivityNotFoundError(Exception):
    pass


class ProgressEnrollmentRequiredError(Exception):
    pass


class ProgressNotStartedError(Exception):
    pass


class ActivityProgressService:
    def __init__(
        self,
        progress: ProgressRepository,
        enrollments: EnrollmentVerifier,
        activities: PublishedActivityLookup,
    ) -> None:
        self.progress, self.enrollments, self.activities = progress, enrollments, activities

    @staticmethod
    def _reference(progress: ActivityProgress) -> ActivityProgressReference:
        return ActivityProgressReference(progress.activity_id, progress.status)

    def _require_access(self, student_user_id: UUID, activity_id: UUID) -> None:
        try:
            activity = self.activities.require_published(activity_id)
        except PublishedActivityNotFoundError as error:
            raise ProgressActivityNotFoundError from error
        if (
            self.enrollments.get_status(student_user_id, activity.course_id)
            is not EnrollmentStatus.ENROLLED
        ):
            raise ProgressEnrollmentRequiredError

    def get_for_student_activity(
        self, student_user_id: UUID, activity_id: UUID
    ) -> ActivityProgressReference | None:
        self._require_access(student_user_id, activity_id)
        progress = self.progress.get(student_user_id, activity_id)
        return None if progress is None else self._reference(progress)

    def start(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgressReference:
        self._require_access(student_user_id, activity_id)
        existing = self.progress.get(student_user_id, activity_id)
        if existing is not None:
            return self._reference(existing)
        return self._reference(
            self.progress.get_or_create(ActivityProgress.start(student_user_id, activity_id))
        )

    def complete(self, student_user_id: UUID, activity_id: UUID) -> ActivityProgressReference:
        self._require_access(student_user_id, activity_id)
        existing = self.progress.get(student_user_id, activity_id)
        if existing is None:
            raise ProgressNotStartedError
        completed = existing.complete()
        return self._reference(
            existing if completed is existing else self.progress.update(completed)
        )
