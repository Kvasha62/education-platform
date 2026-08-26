from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.education.application.published_course_list import PublishedCourseSummary
from app.learning.application.dashboard import ContinueLearningReference
from app.learning.application.enrollment_read import EnrollmentReference
from app.learning.domain.models import EnrollmentStatus
from app.student_space.application.dashboard import StudentDashboardService


class Enrollments:
    def __init__(self, items: list[EnrollmentReference]) -> None:
        self.items = items

    def list_for_student(self, student_user_id: UUID) -> list[EnrollmentReference]:
        return self.items


class Courses:
    def __init__(self, items: list[PublishedCourseSummary]) -> None:
        self.items = items

    def list_published(self) -> list[PublishedCourseSummary]:
        return self.items


class ContinueLearning:
    def __init__(self, item: ContinueLearningReference | None) -> None:
        self.item = item

    def get_for_student(
        self, student_user_id: UUID, enrolled_course_ids: set[UUID]
    ) -> ContinueLearningReference | None:
        return self.item


def enrollment(course_id: UUID, created_at: datetime) -> EnrollmentReference:
    return EnrollmentReference(
        id=uuid4(),
        course_id=course_id,
        status=EnrollmentStatus.ENROLLED,
        created_at=created_at,
    )


def test_dashboard_orders_enrollments_and_excludes_unpublished_or_stale_courses() -> None:
    now = datetime.now(UTC)
    older_course, newer_course, archived_course = uuid4(), uuid4(), uuid4()
    enrollments = [
        enrollment(older_course, now - timedelta(days=1)),
        enrollment(archived_course, now + timedelta(days=1)),
        enrollment(newer_course, now),
    ]
    continue_item = ContinueLearningReference(
        course_id=newer_course,
        activity_id=uuid4(),
        activity_title="Continue activity",
        status="in_progress",
        updated_at=now,
    )
    dashboard = StudentDashboardService(
        Enrollments(enrollments),
        Courses(
            [
                PublishedCourseSummary(older_course, "Older"),
                PublishedCourseSummary(newer_course, "Newer"),
            ]
        ),
        ContinueLearning(continue_item),
    ).get_dashboard(uuid4())

    assert [(item.course_id, item.title) for item in dashboard.my_courses] == [
        (newer_course, "Newer"),
        (older_course, "Older"),
    ]
    assert dashboard.continue_learning is not None
    assert dashboard.continue_learning.activity_id == continue_item.activity_id
    assert dashboard.continue_learning.activity_title == "Continue activity"


def test_dashboard_drops_continue_item_outside_current_enrolled_published_courses() -> None:
    course_id = uuid4()
    continue_item = ContinueLearningReference(
        course_id=course_id,
        activity_id=uuid4(),
        activity_title="Continue activity",
        status="in_progress",
        updated_at=datetime.now(UTC),
    )
    dashboard = StudentDashboardService(
        Enrollments([]),
        Courses([PublishedCourseSummary(course_id, "Published")]),
        ContinueLearning(continue_item),
    ).get_dashboard(uuid4())
    assert dashboard.my_courses == []
    assert dashboard.continue_learning is None
