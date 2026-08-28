"""Authenticated, owner-scoped Teacher Space endpoints."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.assessment.application.services import (
    AssessmentDefinitionAlreadyExistsError,
    AssessmentDefinitionNotFoundError,
)
from app.assessment.domain.models import AssessmentDefinitionImmutableError
from app.identity.api.dependencies import get_current_identity, require_trusted_origin
from app.identity.domain.models import Identity
from app.teacher_space.api.assessment_definition_dependencies import (
    get_teacher_assessment_definition_service,
)
from app.teacher_space.api.assessment_definition_schemas import (
    AssessmentDefinitionResponse,
    CreateAssessmentDefinitionRequest,
    UpdateAssessmentDefinitionRequest,
)
from app.teacher_space.api.dependencies import get_teacher_space_service
from app.teacher_space.api.schemas import (
    CreateTeacherSpaceRequest,
    TeacherSpaceResponse,
    UpdateTeacherSpaceRequest,
)
from app.teacher_space.application.assessment_definitions import (
    AssessmentDefinitionAuthorizationError,
    TeacherAssessmentDefinitionActivityNotFoundError,
    TeacherAssessmentDefinitionService,
)
from app.teacher_space.application.errors import TeacherSpaceNotFoundError
from app.teacher_space.application.services import TeacherSpaceService
from app.teacher_space.domain.models import (
    InvalidTeacherSpaceTransitionError,
    TeacherSpaceDisabledError,
)

router = APIRouter(prefix="/api/v1/teacher-spaces", tags=["teacher-spaces"])

CurrentIdentity = Annotated[Identity, Depends(get_current_identity)]
TeacherSpaces = Annotated[TeacherSpaceService, Depends(get_teacher_space_service)]
AssessmentDefinitions = Annotated[
    TeacherAssessmentDefinitionService,
    Depends(get_teacher_assessment_definition_service),
]

READ_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    status.HTTP_403_FORBIDDEN: {"description": "Assessment access denied"},
    status.HTTP_404_NOT_FOUND: {
        "description": "Teacher Space, Activity, or Assessment Definition not found"
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid request"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
}
MUTATION_ERROR_RESPONSES = {
    **READ_ERROR_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Duplicate Assessment Definition or lifecycle conflict"
    },
}


def _definition_or_error(
    action, *, immutable_detail: str = "Assessment Definition is archived"
) -> Any:
    try:
        return action()
    except TeacherSpaceNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Teacher Space not found") from error
    except TeacherAssessmentDefinitionActivityNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found") from error
    except AssessmentDefinitionNotFoundError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Assessment Definition not found"
        ) from error
    except AssessmentDefinitionAuthorizationError as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Assessment access denied"
        ) from error
    except AssessmentDefinitionAlreadyExistsError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Assessment Definition already exists"
        ) from error
    except TeacherSpaceDisabledError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Disabled Teacher Space is read-only"
        ) from error
    except AssessmentDefinitionImmutableError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, immutable_detail) from error


def not_found(error: TeacherSpaceNotFoundError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Teacher Space not found")


@router.post(
    "",
    response_model=TeacherSpaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trusted_origin)],
)
def create_teacher_space(
    payload: CreateTeacherSpaceRequest,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    teacher_space = service.create(identity.id, payload.name)
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.get("", response_model=list[TeacherSpaceResponse])
def list_teacher_spaces(
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> list[TeacherSpaceResponse]:
    return [
        TeacherSpaceResponse.from_teacher_space(item)
        for item in service.list_owned(identity.id)
    ]


@router.get("/{teacher_space_id}", response_model=TeacherSpaceResponse)
def get_teacher_space(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.get_owned(teacher_space_id, identity.id)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.patch(
    "/{teacher_space_id}",
    response_model=TeacherSpaceResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_teacher_space(
    teacher_space_id: UUID,
    payload: UpdateTeacherSpaceRequest,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.rename(teacher_space_id, identity.id, payload.name)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    except TeacherSpaceDisabledError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Disabled Teacher Space is read-only"
        ) from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.post(
    "/{teacher_space_id}/disable",
    response_model=TeacherSpaceResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def disable_teacher_space(
    teacher_space_id: UUID,
    identity: CurrentIdentity,
    service: TeacherSpaces,
) -> TeacherSpaceResponse:
    try:
        teacher_space = service.disable(teacher_space_id, identity.id)
    except TeacherSpaceNotFoundError as error:
        raise not_found(error) from error
    except InvalidTeacherSpaceTransitionError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "Teacher Space is already disabled") from error
    return TeacherSpaceResponse.from_teacher_space(teacher_space)


@router.get(
    "/{teacher_space_id}/activities/{activity_id}/assessment-definition",
    response_model=AssessmentDefinitionResponse,
    responses=READ_ERROR_RESPONSES,
)
def get_assessment_definition(
    teacher_space_id: UUID,
    activity_id: UUID,
    identity: CurrentIdentity,
    definitions: AssessmentDefinitions,
) -> AssessmentDefinitionResponse:
    definition = _definition_or_error(
        lambda: definitions.get(identity.id, teacher_space_id, activity_id)
    )
    return AssessmentDefinitionResponse.from_definition(definition)


@router.post(
    "/{teacher_space_id}/activities/{activity_id}/assessment-definition",
    response_model=AssessmentDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=MUTATION_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
)
def create_assessment_definition(
    teacher_space_id: UUID,
    activity_id: UUID,
    payload: CreateAssessmentDefinitionRequest,
    identity: CurrentIdentity,
    definitions: AssessmentDefinitions,
) -> AssessmentDefinitionResponse:
    definition = _definition_or_error(
        lambda: definitions.create(
            identity.id,
            teacher_space_id,
            activity_id,
            payload.instructions,
        )
    )
    return AssessmentDefinitionResponse.from_definition(definition)


@router.patch(
    "/{teacher_space_id}/activities/{activity_id}/assessment-definition",
    response_model=AssessmentDefinitionResponse,
    responses=MUTATION_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
)
def update_assessment_definition(
    teacher_space_id: UUID,
    activity_id: UUID,
    payload: UpdateAssessmentDefinitionRequest,
    identity: CurrentIdentity,
    definitions: AssessmentDefinitions,
) -> AssessmentDefinitionResponse:
    definition = _definition_or_error(
        lambda: definitions.update_instructions(
            identity.id,
            teacher_space_id,
            activity_id,
            payload.instructions,
        ),
        immutable_detail="Assessment Definition is archived",
    )
    return AssessmentDefinitionResponse.from_definition(definition)


@router.post(
    "/{teacher_space_id}/activities/{activity_id}/assessment-definition/archive",
    response_model=AssessmentDefinitionResponse,
    responses=MUTATION_ERROR_RESPONSES,
    dependencies=[Depends(require_trusted_origin)],
)
def archive_assessment_definition(
    teacher_space_id: UUID,
    activity_id: UUID,
    identity: CurrentIdentity,
    definitions: AssessmentDefinitions,
) -> AssessmentDefinitionResponse:
    definition = _definition_or_error(
        lambda: definitions.archive(identity.id, teacher_space_id, activity_id),
        immutable_detail="Assessment Definition is already archived",
    )
    return AssessmentDefinitionResponse.from_definition(definition)
