"""Teacher Space dependency wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.application.definition_lookup import AssessmentDefinitionIdLookup
from app.assessment.composition import (
    get_assessment_attempt_detail_service,
    get_assessment_attempt_service,
    get_assessment_definition_id_lookup,
    get_assessment_result_service,
)
from app.core.database import get_db
from app.education.composition import get_activity_teacher_space_scope_query
from app.teacher_space.application.assessment_results import TeacherAssessmentReviewService
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.infrastructure.repositories import SqlAlchemyTeacherSpaceRepository


def get_teacher_space_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherSpaceService:
    return TeacherSpaceService(SqlAlchemyTeacherSpaceRepository(db))


def get_teacher_assessment_review_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherAssessmentReviewService:
    return TeacherAssessmentReviewService(
        get_teacher_space_service(db),
        get_activity_teacher_space_scope_query(db),
        get_assessment_attempt_service(db),
        get_assessment_attempt_detail_service(db),
        get_assessment_result_service(db),
    )


def get_teacher_activity_assessment_lookup(
    assessments: Annotated[
        AssessmentDefinitionIdLookup,
        Depends(get_assessment_definition_id_lookup),
    ],
) -> AssessmentDefinitionIdLookup:
    return assessments
