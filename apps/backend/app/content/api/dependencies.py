from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.content.application.services import ContentService
from app.content.infrastructure.repositories import SqlAlchemyContentRepository
from app.content.public import ContentLookup, ContentLookupService
from app.core.database import get_db


def get_content_service(db: Annotated[Session, Depends(get_db)]) -> ContentService:
    return ContentService(SqlAlchemyContentRepository(db))


def get_content_lookup(db: Annotated[Session, Depends(get_db)]) -> ContentLookup:
    return ContentLookupService(SqlAlchemyContentRepository(db))
