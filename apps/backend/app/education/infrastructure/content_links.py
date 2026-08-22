"""SQLAlchemy persistence for Education-owned Activity / Content links."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.education.application.errors import ActivityNotFoundError
from app.education.domain.content_links import ActivityContentLink
from app.education.infrastructure.models import ActivityContentLinkModel


def _to_domain(model: ActivityContentLinkModel) -> ActivityContentLink:
    return ActivityContentLink(model.activity_id, model.content_id)


class SqlAlchemyActivityContentLinkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def attach(self, link: ActivityContentLink) -> ActivityContentLink:
        existing = self.db.get(ActivityContentLinkModel, (link.activity_id, link.content_id))
        if existing is not None:
            return _to_domain(existing)

        model = ActivityContentLinkModel(
            activity_id=link.activity_id,
            content_id=link.content_id,
        )
        try:
            with self.db.begin_nested():
                self.db.add(model)
                self.db.flush()
        except IntegrityError as error:
            existing = self.db.get(ActivityContentLinkModel, (link.activity_id, link.content_id))
            if existing is not None:
                return _to_domain(existing)
            raise ActivityNotFoundError from error
        return _to_domain(model)

    def detach(self, activity_id: UUID, content_id: UUID) -> None:
        model = self.db.get(ActivityContentLinkModel, (activity_id, content_id))
        if model is None:
            return
        self.db.delete(model)
        self.db.flush()

    def list_for_activity(self, activity_id: UUID) -> list[ActivityContentLink]:
        models = self.db.scalars(
            select(ActivityContentLinkModel)
            .where(ActivityContentLinkModel.activity_id == activity_id)
            .order_by(ActivityContentLinkModel.content_id)
        ).all()
        return [_to_domain(model) for model in models]

    def list_for_content(self, content_id: UUID) -> list[ActivityContentLink]:
        models = self.db.scalars(
            select(ActivityContentLinkModel)
            .where(ActivityContentLinkModel.content_id == content_id)
            .order_by(ActivityContentLinkModel.activity_id)
        ).all()
        return [_to_domain(model) for model in models]

    def exists(self, activity_id: UUID, content_id: UUID) -> bool:
        return self.db.get(ActivityContentLinkModel, (activity_id, content_id)) is not None
