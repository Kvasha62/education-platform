from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.education.application.activity_publication import PublishedActivityReference
from app.learning.application.dashboard import ContinueLearningService
from app.learning.domain.progress import ActivityProgress, ProgressStatus


class ProgressRepository:
    def __init__(self, items: list[ActivityProgress]) -> None:
        self.items = items

    def list_in_progress(self, student_user_id: UUID) -> list[ActivityProgress]:
        return [item for item in self.items if item.student_user_id == student_user_id]


class Activities:
    def __init__(self, references: list[PublishedActivityReference]) -> None:
        self.references = references
        self.requested: list[UUID] = []

    def list_published(
        self, activity_ids: list[UUID]
    ) -> dict[UUID, PublishedActivityReference]:
        self.requested = activity_ids
        return {
            item.id: item for item in self.references if item.id in activity_ids
        }


def progress(student_id: UUID, activity_id: UUID, updated_at: datetime) -> ActivityProgress:
    return ActivityProgress(
        id=uuid4(),
        student_user_id=student_id,
        activity_id=activity_id,
        status=ProgressStatus.IN_PROGRESS,
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_continue_learning_chooses_latest_student_visible_in_progress_activity() -> None:
    student_id = uuid4()
    now = datetime.now(UTC)
    stale_activity, visible_activity = uuid4(), uuid4()
    candidates = [
        progress(student_id, stale_activity, now),
        progress(student_id, visible_activity, now - timedelta(minutes=1)),
    ]
    course_id = uuid4()
    activities = Activities([PublishedActivityReference(visible_activity, course_id)])

    result = ContinueLearningService(
        ProgressRepository(candidates), activities
    ).get_for_student(student_id)

    assert result is not None
    assert result.course_id == course_id
    assert result.activity_id == visible_activity
    assert result.status == "in_progress"
    assert activities.requested == [stale_activity, visible_activity]


def test_continue_learning_is_empty_without_visible_in_progress_activity() -> None:
    student_id = uuid4()
    candidate = progress(student_id, uuid4(), datetime.now(UTC))
    result = ContinueLearningService(
        ProgressRepository([candidate]), Activities([])
    ).get_for_student(student_id)
    assert result is None
