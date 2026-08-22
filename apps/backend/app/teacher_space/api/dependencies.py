"""Teacher Space dependency wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository


def get_teacher_space_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherSpaceService:
    return TeacherSpaceService(SqlAlchemyTeacherSpaceRepository(db))
