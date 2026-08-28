"""Teacher AssessmentDefinition management dependency wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.composition import get_assessment_definition_service
from app.core.database import get_db
from app.education.composition import get_activity_teacher_space_scope_query
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.application.assessment_definitions import (
    TeacherAssessmentDefinitionService,
)


def get_teacher_assessment_definition_service(
    db: Annotated[Session, Depends(get_db)],
) -> TeacherAssessmentDefinitionService:
    return TeacherAssessmentDefinitionService(
        get_teacher_space_service(db),
        get_activity_teacher_space_scope_query(db),
        get_assessment_definition_service(db),
    )
