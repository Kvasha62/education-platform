"""Student Dashboard aggregate contract.

MVP includes enrolled published Courses and one deterministic Continue Learning item.
Recent Learning is excluded because read/visit events are not persisted. Progress Overview is
excluded because no approved Course-level progress/completion semantics exist.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from app.education.application.published_course_list import PublishedCourseListReader
from app.learning.application.dashboard import ContinueLearningReader
from app.learning.application.enrollment_read import StudentEnrollmentReader


@dataclass(frozen=True, slots=True)
class DashboardCourse:
    course_id: UUID
    title: str
    status: Literal["enrolled"]
    enrolled_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardContinueLearning:
    course_id: UUID
    activity_id: UUID
    status: Literal["in_progress"]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StudentDashboard:
    my_courses: list[DashboardCourse]
    continue_learning: DashboardContinueLearning | None


class StudentDashboardReader(Protocol):
    def get_dashboard(self, student_user_id: UUID) -> StudentDashboard: ...


class StudentDashboardService:
    """Compose existing Education and Learning readers in four bounded queries or fewer."""

    def __init__(
        self,
        enrollments: StudentEnrollmentReader,
        courses: PublishedCourseListReader,
        continue_learning: ContinueLearningReader,
    ) -> None:
        self.enrollments = enrollments
        self.courses = courses
        self.continue_learning = continue_learning

    def get_dashboard(self, student_user_id: UUID) -> StudentDashboard:
        published = {course.id: course for course in self.courses.list_published()}
        enrollments = sorted(
            self.enrollments.list_for_student(student_user_id),
            key=lambda item: (item.created_at, item.id),
            reverse=True,
        )
        my_courses = [
            DashboardCourse(
                course_id=enrollment.course_id,
                title=published[enrollment.course_id].title,
                status="enrolled",
                enrolled_at=enrollment.created_at,
            )
            for enrollment in enrollments
            if enrollment.course_id in published
        ]
        if not my_courses:
            return StudentDashboard(my_courses=[], continue_learning=None)

        enrolled_course_ids = {course.course_id for course in my_courses}
        resumable = self.continue_learning.get_for_student(
            student_user_id, enrolled_course_ids
        )
        continue_item = (
            DashboardContinueLearning(
                course_id=resumable.course_id,
                activity_id=resumable.activity_id,
                status=resumable.status,
                updated_at=resumable.updated_at,
            )
            if resumable is not None and resumable.course_id in enrolled_course_ids
            else None
        )
        return StudentDashboard(
            my_courses=my_courses,
            continue_learning=continue_item,
        )
