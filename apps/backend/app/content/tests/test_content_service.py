from typing import Any
from uuid import uuid4

import pytest

from app.content.application.errors import ContentNotFoundError
from app.content.application.services import ContentService
from app.content.domain.models import ContentStatus, ContentType, InvalidContentTitleError


class MemoryRepository:
    def __init__(self) -> None:
        self.items: dict[Any, Any] = {}

    def add(self, item):
        self.items[item.id] = item
        return item

    def list_owned(self, owner):
        return [item for item in self.items.values() if item.owner_user_id == owner]

    def get_owned(self, item_id, owner):
        item = self.items.get(item_id)
        return item if item and item.owner_user_id == owner else None

    def update(self, item):
        self.items[item.id] = item
        return item

    def delete(self, item):
        self.items.pop(item.id, None)


@pytest.fixture
def service() -> ContentService:
    return ContentService(MemoryRepository())


@pytest.mark.parametrize("kind", list(ContentType))
def test_create_draft_owned_content(service: ContentService, kind: ContentType) -> None:
    owner = uuid4()
    content = service.create(owner, kind, " Title ")
    assert (content.owner_user_id, content.type, content.title, content.status) == (
        owner,
        kind,
        "Title",
        ContentStatus.DRAFT,
    )


@pytest.mark.parametrize("title", ["", " ", "x" * 121])
def test_invalid_title(service: ContentService, title: str) -> None:
    with pytest.raises(InvalidContentTitleError):
        service.create(uuid4(), ContentType.ARTICLE, title)


def test_rename_preserves_owner_type_and_status(service: ContentService) -> None:
    owner = uuid4()
    item = service.create(owner, ContentType.RESOURCE, "Old")
    changed = service.rename(item.id, owner, "New")
    assert (changed.title, changed.owner_user_id, changed.type, changed.status) == (
        "New",
        owner,
        ContentType.RESOURCE,
        ContentStatus.DRAFT,
    )


def test_cross_owner_is_not_found(service: ContentService) -> None:
    item = service.create(uuid4(), ContentType.ARTICLE, "Private")
    with pytest.raises(ContentNotFoundError):
        service.get_owned(item.id, uuid4())


def test_publish_draft_and_repeat_idempotently(service: ContentService) -> None:
    owner = uuid4()
    draft = service.create(owner, ContentType.ARTICLE, "Publishable")

    published = service.publish(draft.id, owner)
    repeated = service.publish(draft.id, owner)

    assert published.status is ContentStatus.PUBLISHED
    assert repeated == published
    assert repeated.updated_at == published.updated_at


def test_publish_cross_owner_is_not_found(service: ContentService) -> None:
    item = service.create(uuid4(), ContentType.ARTICLE, "Private")
    with pytest.raises(ContentNotFoundError):
        service.publish(item.id, uuid4())


def test_delete(service: ContentService) -> None:
    owner = uuid4()
    item = service.create(owner, ContentType.ARTICLE, "Temporary")
    service.delete(item.id, owner)
    with pytest.raises(ContentNotFoundError):
        service.get_owned(item.id, owner)
