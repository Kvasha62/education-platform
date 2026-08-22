from uuid import UUID

from app.content.application.errors import ContentNotFoundError
from app.content.application.ports import ContentRepository
from app.content.domain.models import Content, ContentType


class ContentService:
    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    def create(self, owner_user_id: UUID, content_type: ContentType, title: str) -> Content:
        return self.repository.add(Content.create(owner_user_id, content_type, title))

    def list_owned(self, owner_user_id: UUID) -> list[Content]:
        return self.repository.list_owned(owner_user_id)

    def get_owned(self, content_id: UUID, owner_user_id: UUID) -> Content:
        content = self.repository.get_owned(content_id, owner_user_id)
        if content is None:
            raise ContentNotFoundError
        return content

    def rename(self, content_id: UUID, owner_user_id: UUID, title: str) -> Content:
        return self.repository.update(self.get_owned(content_id, owner_user_id).rename(title))

    def publish(self, content_id: UUID, owner_user_id: UUID) -> Content:
        content = self.get_owned(content_id, owner_user_id)
        published = content.publish()
        return content if published is content else self.repository.update(published)

    def delete(self, content_id: UUID, owner_user_id: UUID) -> None:
        self.repository.delete(self.get_owned(content_id, owner_user_id))
