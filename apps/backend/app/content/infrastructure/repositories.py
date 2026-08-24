from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.application.errors import ContentNotFoundError
from app.content.domain.models import Content
from app.content.infrastructure.models import ContentModel


def _to_domain(model: ContentModel) -> Content:
    return Content(
        id=model.id,
        owner_user_id=model.owner_user_id,
        type=model.type,
        title=model.title,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyContentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, content: Content) -> Content:
        model = ContentModel(
            id=content.id,
            owner_user_id=content.owner_user_id,
            type=content.type,
            title=content.title,
            status=content.status,
            created_at=content.created_at,
            updated_at=content.updated_at,
        )
        self.db.add(model)
        self.db.flush()
        return _to_domain(model)

    def list_owned(self, owner_user_id: UUID) -> list[Content]:
        models = self.db.scalars(
            select(ContentModel)
            .where(ContentModel.owner_user_id == owner_user_id)
            .order_by(ContentModel.created_at, ContentModel.id)
        ).all()
        return [_to_domain(model) for model in models]

    def get_by_id(self, content_id: UUID) -> Content | None:
        model = self.db.get(ContentModel, content_id)
        return _to_domain(model) if model else None

    def get_owned(self, content_id: UUID, owner_user_id: UUID) -> Content | None:
        model = self.db.scalar(
            select(ContentModel).where(
                ContentModel.id == content_id,
                ContentModel.owner_user_id == owner_user_id,
            )
        )
        return _to_domain(model) if model else None

    def update(self, content: Content) -> Content:
        model = self.db.get(ContentModel, content.id)
        if model is None:
            raise ContentNotFoundError
        model.title = content.title
        model.status = content.status
        model.updated_at = content.updated_at
        self.db.flush()
        return _to_domain(model)

    def delete(self, content: Content) -> None:
        model = self.db.get(ContentModel, content.id)
        if model is None:
            raise ContentNotFoundError
        self.db.delete(model)
        self.db.flush()
