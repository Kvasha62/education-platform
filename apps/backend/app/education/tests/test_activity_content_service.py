from typing import cast
from uuid import UUID, uuid4

import pytest

from app.content.public import (
    ContentLookupUnavailable,
    ContentReference,
    ContentReferenceNotFound,
    ContentStatus,
    ContentType,
)
from app.education.application.content_links import ActivityContentService
from app.education.application.errors import (
    ActivityNotFoundError,
    LinkedContentNotFoundError,
    LinkedContentUnavailableError,
)
from app.education.application.ports import ActivityRepository
from app.education.application.services import ActivityService
from app.education.domain.content_links import ActivityContentLink
from app.education.domain.models import Activity, ActivityType, Course, CourseImmutableError


class MemoryActivityRepository:
    def __init__(self, activity: Activity) -> None:
        self.activity = activity

    def get_in_unit(self, activity_id: UUID, unit_id: UUID) -> Activity | None:
        if self.activity.id == activity_id and self.activity.learning_unit_id == unit_id:
            return self.activity
        return None


class MemoryLinkRepository:
    def __init__(self) -> None:
        self.links: set[ActivityContentLink] = set()

    def attach(self, link: ActivityContentLink) -> ActivityContentLink:
        self.links.add(link)
        return link

    def detach(self, activity_id: UUID, content_id: UUID) -> None:
        self.links.discard(ActivityContentLink(activity_id, content_id))

    def list_for_activity(self, activity_id: UUID) -> list[ActivityContentLink]:
        return sorted(
            (link for link in self.links if link.activity_id == activity_id),
            key=lambda link: link.content_id,
        )

    def list_for_content(self, content_id: UUID) -> list[ActivityContentLink]:
        return sorted(
            (link for link in self.links if link.content_id == content_id),
            key=lambda link: link.activity_id,
        )

    def exists(self, activity_id: UUID, content_id: UUID) -> bool:
        return ActivityContentLink(activity_id, content_id) in self.links


class FakeContentLookup:
    def __init__(self) -> None:
        self.references: dict[tuple[UUID, UUID], ContentReference] = {}
        self.unavailable = False

    def add(self, owner_id: UUID, content_id: UUID, status: ContentStatus) -> None:
        self.references[(owner_id, content_id)] = ContentReference(
            id=content_id,
            type=ContentType.ARTICLE,
            status=status,
            available_for_student=status is ContentStatus.PUBLISHED,
        )

    def lookup_owned(self, content_id: UUID, owner_user_id: UUID) -> ContentReference:
        if self.unavailable:
            raise ContentLookupUnavailable
        try:
            return self.references[(owner_user_id, content_id)]
        except KeyError as error:
            raise ContentReferenceNotFound from error

    def lookup_published(self, content_id: UUID) -> ContentReference:
        if self.unavailable:
            raise ContentLookupUnavailable
        reference = next(
            (
                item
                for (_owner_id, item_id), item in self.references.items()
                if item_id == content_id
            ),
            None,
        )
        if reference is None or reference.status is not ContentStatus.PUBLISHED:
            raise ContentReferenceNotFound
        return reference


def build_service() -> tuple[
    ActivityContentService,
    Course,
    Activity,
    MemoryLinkRepository,
    FakeContentLookup,
]:
    course = Course.create(uuid4(), "Course")
    activity = Activity.create(uuid4(), "Activity", ActivityType.LECTURE, 0)
    links = MemoryLinkRepository()
    lookup = FakeContentLookup()
    activities = ActivityService(cast(ActivityRepository, MemoryActivityRepository(activity)))
    service = ActivityContentService(activities, links, lookup)
    return service, course, activity, links, lookup


@pytest.mark.parametrize("status", [ContentStatus.DRAFT, ContentStatus.PUBLISHED])
def test_attach_owned_draft_or_published_content(status: ContentStatus) -> None:
    service, course, activity, links, lookup = build_service()
    owner_id, content_id = uuid4(), uuid4()
    lookup.add(owner_id, content_id, status)

    link = service.attach(activity.id, activity.learning_unit_id, content_id, owner_id, course)

    assert link == ActivityContentLink(activity.id, content_id)
    assert links.exists(activity.id, content_id)


def test_repeated_attach_is_idempotent() -> None:
    service, course, activity, links, lookup = build_service()
    owner_id, content_id = uuid4(), uuid4()
    lookup.add(owner_id, content_id, ContentStatus.DRAFT)

    first = service.attach(activity.id, activity.learning_unit_id, content_id, owner_id, course)
    second = service.attach(activity.id, activity.learning_unit_id, content_id, owner_id, course)

    assert first == second
    assert links.list_for_activity(activity.id) == [first]


def test_attach_validates_activity_scope() -> None:
    service, course, activity, _, lookup = build_service()
    owner_id, content_id = uuid4(), uuid4()
    lookup.add(owner_id, content_id, ContentStatus.PUBLISHED)

    with pytest.raises(ActivityNotFoundError):
        service.attach(activity.id, uuid4(), content_id, owner_id, course)


def test_missing_and_cross_owner_content_are_isolated() -> None:
    service, course, activity, _, lookup = build_service()
    actual_owner, other_owner, content_id = uuid4(), uuid4(), uuid4()
    lookup.add(actual_owner, content_id, ContentStatus.PUBLISHED)

    with pytest.raises(LinkedContentNotFoundError):
        service.attach(activity.id, activity.learning_unit_id, content_id, other_owner, course)
    with pytest.raises(LinkedContentNotFoundError):
        service.attach(activity.id, activity.learning_unit_id, uuid4(), actual_owner, course)


def test_detach_is_idempotent() -> None:
    service, course, activity, links, lookup = build_service()
    owner_id, content_id = uuid4(), uuid4()
    lookup.add(owner_id, content_id, ContentStatus.PUBLISHED)
    service.attach(activity.id, activity.learning_unit_id, content_id, owner_id, course)

    service.detach(activity.id, activity.learning_unit_id, content_id, course)
    service.detach(activity.id, activity.learning_unit_id, content_id, course)

    assert not links.exists(activity.id, content_id)


def test_stale_content_is_resolved_as_unavailable() -> None:
    service, _, activity, links, _ = build_service()
    stale_id = uuid4()
    links.attach(ActivityContentLink(activity.id, stale_id))

    resolved = service.resolve_for_activity(activity.id, activity.learning_unit_id, uuid4())

    assert len(resolved) == 1
    assert resolved[0].link.content_id == stale_id
    assert resolved[0].type is None
    assert resolved[0].status is None
    assert not resolved[0].available
    assert not resolved[0].available_for_student


def test_technical_lookup_failure_remains_distinct() -> None:
    service, _, activity, links, lookup = build_service()
    links.attach(ActivityContentLink(activity.id, uuid4()))
    lookup.unavailable = True

    with pytest.raises(LinkedContentUnavailableError):
        service.resolve_for_activity(activity.id, activity.learning_unit_id, uuid4())


def test_student_availability_includes_only_published_content() -> None:
    service, course, activity, _, lookup = build_service()
    owner_id, draft_id, published_id = uuid4(), uuid4(), uuid4()
    lookup.add(owner_id, draft_id, ContentStatus.DRAFT)
    lookup.add(owner_id, published_id, ContentStatus.PUBLISHED)
    service.attach(activity.id, activity.learning_unit_id, draft_id, owner_id, course)
    service.attach(activity.id, activity.learning_unit_id, published_id, owner_id, course)

    available = service.list_student_available(activity.id, activity.learning_unit_id)

    assert [item.link.content_id for item in available] == [published_id]
    assert all(item.available_for_student for item in available)


def test_immutable_course_blocks_attach_and_detach_in_application() -> None:
    service, course, activity, _, lookup = build_service()
    owner_id, content_id = uuid4(), uuid4()
    lookup.add(owner_id, content_id, ContentStatus.PUBLISHED)
    service.attach(activity.id, activity.learning_unit_id, content_id, owner_id, course)
    published = course.publish()

    with pytest.raises(CourseImmutableError):
        service.attach(
            activity.id,
            activity.learning_unit_id,
            content_id,
            owner_id,
            published,
        )
    with pytest.raises(CourseImmutableError):
        service.detach(activity.id, activity.learning_unit_id, content_id, published)
