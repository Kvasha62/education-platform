"""Authoritative Learning-owned Student Course Progress aggregation."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.education.application.activity_publication import PublishedCourseActivityReader
from app.education.application.errors import PublishedCourseNotFoundError
from app.learning.application.progress import EnrollmentVerifier
from app.learning.domain.models import EnrollmentStatus


@dataclass(frozen=True, slots=True)
class CourseProgress:
    course_id: UUID
    completed_activities: int
    total_activities: int
    progress_percent: int


class CompletedActivityCounter(Protocol):
    def count_completed(
        self, student_user_id: UUID, activity_ids: list[UUID]
    ) -> int: ...


class CourseProgressReader(Protocol):
    def get_for_student(self, student_user_id: UUID, course_id: UUID) -> CourseProgress: ...


class CourseProgressNotFoundError(Exception):
    """Safe error for an unavailable or inaccessible Student Course."""


class CourseProgressService:
    def __init__(
        self,
        activities: PublishedCourseActivityReader,
        enrollments: EnrollmentVerifier,
        progress: CompletedActivityCounter,
    ) -> None:
        self.activities = activities
        self.enrollments = enrollments
        self.progress = progress

    def get_for_student(self, student_user_id: UUID, course_id: UUID) -> CourseProgress:
        try:
            activity_ids = self.activities.list_activity_ids(course_id)
        except PublishedCourseNotFoundError as error:
            raise CourseProgressNotFoundError from error
        if self.enrollments.get_status(student_user_id, course_id) is not EnrollmentStatus.ENROLLED:
            raise CourseProgressNotFoundError

        total = len(activity_ids)
        completed = self.progress.count_completed(student_user_id, activity_ids)
        percent = completed * 100 // total if total else 0
        return CourseProgress(course_id, completed, total, percent)
