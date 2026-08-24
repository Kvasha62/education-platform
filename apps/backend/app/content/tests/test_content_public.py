from uuid import uuid4

import pytest

from app.content.domain.models import Content, ContentStatus, ContentType
from app.content.public import (
    ContentLookupService,
    ContentLookupUnavailable,
    ContentReferenceNotFound,
)


class LookupRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[object, object], Content] = {}
        self.fail = False

    def get_by_id(self, content_id):
        if self.fail:
            raise RuntimeError("database unavailable")
        return next(
            (
                content
                for (item_id, _owner_id), content in self.items.items()
                if item_id == content_id
            ),
            None,
        )

    def get_owned(self, content_id, owner_user_id):
        if self.fail:
            raise RuntimeError("database unavailable")
        return self.items.get((content_id, owner_user_id))


def test_public_lookup_returns_safe_reference_and_student_availability() -> None:
    repository = LookupRepository()
    owner_id = uuid4()
    draft = Content.create(owner_id, ContentType.ARTICLE, "Draft")
    published = Content.create(owner_id, ContentType.RESOURCE, "Published").publish()
    repository.items[(draft.id, owner_id)] = draft
    repository.items[(published.id, owner_id)] = published
    service = ContentLookupService(repository)  # type: ignore[arg-type]

    draft_reference = service.lookup_owned(draft.id, owner_id)
    published_reference = service.lookup_owned(published.id, owner_id)

    assert not draft_reference.available_for_student
    assert draft_reference.status is ContentStatus.DRAFT
    assert published_reference.available_for_student
    assert published_reference.status is ContentStatus.PUBLISHED
    assert not hasattr(published_reference, "owner_user_id")
    assert not hasattr(published_reference, "title")


def test_public_lookup_hides_missing_and_cross_owner_content() -> None:
    repository = LookupRepository()
    owner_id = uuid4()
    content = Content.create(owner_id, ContentType.ARTICLE, "Private")
    repository.items[(content.id, owner_id)] = content
    service = ContentLookupService(repository)  # type: ignore[arg-type]

    with pytest.raises(ContentReferenceNotFound):
        service.lookup_owned(content.id, uuid4())
    with pytest.raises(ContentReferenceNotFound):
        service.lookup_owned(uuid4(), owner_id)


def test_published_lookup_exposes_only_published_content() -> None:
    repository = LookupRepository()
    owner_id = uuid4()
    draft = Content.create(owner_id, ContentType.ARTICLE, "Draft")
    published = Content.create(owner_id, ContentType.RESOURCE, "Published").publish()
    repository.items[(draft.id, owner_id)] = draft
    repository.items[(published.id, owner_id)] = published
    service = ContentLookupService(repository)  # type: ignore[arg-type]

    reference = service.lookup_published(published.id)
    assert reference.id == published.id
    assert reference.available_for_student
    with pytest.raises(ContentReferenceNotFound):
        service.lookup_published(draft.id)
    with pytest.raises(ContentReferenceNotFound):
        service.lookup_published(uuid4())


def test_public_lookup_preserves_technical_failure() -> None:
    repository = LookupRepository()
    repository.fail = True
    service = ContentLookupService(repository)  # type: ignore[arg-type]

    with pytest.raises(ContentLookupUnavailable):
        service.lookup_owned(uuid4(), uuid4())
    with pytest.raises(ContentLookupUnavailable):
        service.lookup_published(uuid4())
