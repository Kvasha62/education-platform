from uuid import UUID, uuid4

import pytest

from app.education.application.errors import PublishedCourseNotFoundError
from app.learning.application.course_progress import (
    CourseProgressNotFoundError,
    CourseProgressService,
)
from app.learning.domain.models import EnrollmentStatus


class Activities:
    def __init__(self, ids: list[UUID] | None) -> None:
        self.ids = ids
        self.calls = 0

    def list_activity_ids(self, course_id: UUID) -> list[UUID]:
        self.calls += 1
        if self.ids is None:
            raise PublishedCourseNotFoundError
        return self.ids


class Enrollments:
    def __init__(self, status: EnrollmentStatus | None) -> None:
        self.status = status
        self.calls = 0

    def get_status(self, student_user_id: UUID, course_id: UUID) -> EnrollmentStatus | None:
        self.calls += 1
        return self.status


class Progress:
    def __init__(self, completed: int) -> None:
        self.completed = completed
        self.calls: list[tuple[UUID, list[UUID]]] = []

    def count_completed(self, student_user_id: UUID, activity_ids: list[UUID]) -> int:
        self.calls.append((student_user_id, activity_ids))
        return self.completed


def service(
    activity_ids: list[UUID] | None,
    completed: int,
    enrollment: EnrollmentStatus | None = EnrollmentStatus.ENROLLED,
) -> tuple[CourseProgressService, Activities, Enrollments, Progress]:
    activities = Activities(activity_ids)
    enrollments = Enrollments(enrollment)
    progress = Progress(completed)
    return (
        CourseProgressService(activities, enrollments, progress),
        activities,
        enrollments,
        progress,
    )


@pytest.mark.parametrize(
    ("total", "completed", "percent"),
    [(0, 0, 0), (3, 0, 0), (3, 1, 33), (3, 2, 66), (3, 3, 100)],
)
def test_course_progress_uses_floor_percentage(
    total: int, completed: int, percent: int
) -> None:
    activity_ids = [uuid4() for _ in range(total)]
    reader, activities, enrollments, progress = service(activity_ids, completed)
    student_id, course_id = uuid4(), uuid4()

    result = reader.get_for_student(student_id, course_id)

    assert result.course_id == course_id
    assert result.completed_activities == completed
    assert result.total_activities == total
    assert result.progress_percent == percent
    assert activities.calls == enrollments.calls == 1
    assert progress.calls == [(student_id, activity_ids)]


def test_course_progress_rejects_non_enrolled_student() -> None:
    reader, _activities, _enrollments, progress = service([uuid4()], 0, None)
    with pytest.raises(CourseProgressNotFoundError):
        reader.get_for_student(uuid4(), uuid4())
    assert progress.calls == []


def test_course_progress_hides_unknown_or_unpublished_course_before_enrollment_lookup() -> None:
    reader, activities, enrollments, progress = service(None, 0)
    with pytest.raises(CourseProgressNotFoundError):
        reader.get_for_student(uuid4(), uuid4())
    assert activities.calls == 1
    assert enrollments.calls == 0
    assert progress.calls == []
