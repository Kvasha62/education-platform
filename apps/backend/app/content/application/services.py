from dataclasses import dataclass
from uuid import UUID

from app.content.application.errors import ContentNotFoundError
from app.content.application.ports import ContentRepository
from app.content.domain.body import ContentBody
from app.content.domain.models import Content, ContentType


@dataclass(frozen=True, slots=True)
class ContentPage:
    items: list[Content]
    has_next: bool


class ContentService:
    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    def create(self, owner_user_id: UUID, content_type: ContentType, title: str) -> Content:
        return self.repository.add(Content.create(owner_user_id, content_type, title))

    def list_owned(self, owner_user_id: UUID, *, page: int, page_size: int) -> ContentPage:
        items = self.repository.list_owned(
            owner_user_id,
            offset=(page - 1) * page_size,
            limit=page_size + 1,
        )
        return ContentPage(items=items[:page_size], has_next=len(items) > page_size)

    def get_owned(self, content_id: UUID, owner_user_id: UUID) -> Content:
        content = self.repository.get_owned(content_id, owner_user_id)
        if content is None:
            raise ContentNotFoundError
        return content

    def get_owned_body(self, content_id: UUID, owner_user_id: UUID) -> ContentBody:
        return self.get_owned(content_id, owner_user_id).body

    def replace_owned_body(
        self, content_id: UUID, owner_user_id: UUID, body: ContentBody
    ) -> ContentBody:
        updated = self.repository.update(
            self.get_owned(content_id, owner_user_id).replace_body(body)
        )
        return updated.body

    def rename(self, content_id: UUID, owner_user_id: UUID, title: str) -> Content:
        return self.repository.update(self.get_owned(content_id, owner_user_id).rename(title))

    def publish(self, content_id: UUID, owner_user_id: UUID) -> Content:
        content = self.get_owned(content_id, owner_user_id)
        published = content.publish()
        return content if published is content else self.repository.update(published)

    def delete(self, content_id: UUID, owner_user_id: UUID) -> None:
        self.repository.delete(self.get_owned(content_id, owner_user_id))
