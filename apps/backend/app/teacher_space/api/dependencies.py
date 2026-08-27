"""Teacher Space dependency wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.composition import get_assessment_result_service
from app.core.database import get_db
from app.education.composition import get_activity_teacher_space_scope_query
from app.teacher_space.application.assessment_results import TeacherAssessmentResultService
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository


def get_teacher_space_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherSpaceService:
    return TeacherSpaceService(SqlAlchemyTeacherSpaceRepository(db))


def get_teacher_assessment_result_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherAssessmentResultService:
    return TeacherAssessmentResultService(
        get_teacher_space_service(db),
        get_activity_teacher_space_scope_query(db),
        get_assessment_result_service(db),
        db.begin,
    )
